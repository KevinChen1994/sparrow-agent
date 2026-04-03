from __future__ import annotations

from datetime import datetime, timezone

from sparrow_agent.core.bootstrap import BootstrapManager
from sparrow_agent.core.consolidator import SessionConsolidator
from sparrow_agent.core.context_loader import ContextLoader
from sparrow_agent.core.halt_policy import HaltPolicy
from sparrow_agent.core.react_loop import ReActLoop
from sparrow_agent.llm.base import ModelClient
from sparrow_agent.llm.openai_client import build_default_model_client
from sparrow_agent.memory.store import MemoryStore
from sparrow_agent.schemas.models import LoopState, Message, RuntimeContext, TurnResult
from sparrow_agent.storage.file_store import FileStore
from sparrow_agent.tools.filesystem import EditFileTool, EchoTool, ListDirTool, ReadFileTool, WriteFileTool
from sparrow_agent.tools.memory_docs import build_memory_tools
from sparrow_agent.tools.registry import ToolRegistry
from sparrow_agent.capabilities.mcp import MCPAdapter, MCPServerSpec
from sparrow_agent.capabilities.skills import SkillRegistry, load_default_skills


class AgentRuntime:
    def __init__(
        self,
        file_store: FileStore | None = None,
        memory_store: MemoryStore | None = None,
        tool_registry: ToolRegistry | None = None,
        skill_registry: SkillRegistry | None = None,
        model_client: ModelClient | None = None,
        max_iterations: int = 40,
        memory_window: int = 100,
        tool_result_max_chars: int = 500,
    ) -> None:
        self.file_store = file_store or FileStore()
        self.memory_store = memory_store or MemoryStore(self.file_store)
        self.context_loader = ContextLoader(self.file_store)
        self.bootstrap = BootstrapManager(self.file_store)
        self.skill_registry = skill_registry or SkillRegistry(load_default_skills())
        self.model_client = model_client or build_default_model_client()
        self.tool_registry = tool_registry or self._build_default_tool_registry()
        self.halt_policy = HaltPolicy(max_iterations=max_iterations)
        self.react_loop = ReActLoop(
            self.model_client,
            self.tool_registry,
            self.halt_policy,
            refresh_documents=lambda: self.context_loader.load().documents,
        )
        self.consolidator = SessionConsolidator(
            file_store=self.file_store,
            memory_window=memory_window,
            tool_result_max_chars=tool_result_max_chars,
        )
        self.mcp_adapter = MCPAdapter(self.tool_registry)

    def start_session(self, session_id: str) -> TurnResult:
        session = self.file_store.load_session(session_id)
        self.context_loader.load()

        if not self.bootstrap.should_prompt(len(session.messages)):
            return TurnResult(session_id=session_id, reply="", messages=session.messages)

        prompt = self.bootstrap.build_prompt()
        if not session.messages or session.messages[-1].role != "assistant" or session.messages[-1].content != prompt:
            session.messages.append(Message(role="assistant", content=prompt))
            session.updated_at = datetime.now(timezone.utc)
            self.file_store.save_session(session)

        return TurnResult(
            session_id=session_id,
            reply=prompt,
            messages=session.messages,
        )

    def _build_default_tool_registry(self) -> ToolRegistry:
        workspace = self.file_store.workspace_root
        tools = [
            EchoTool(),
            ReadFileTool(workspace=workspace),
            WriteFileTool(workspace=workspace),
            EditFileTool(workspace=workspace),
            ListDirTool(workspace=workspace),
            *build_memory_tools(self.file_store),
        ]
        return ToolRegistry(tools)

    def run_turn(self, session_id: str, user_input: str) -> TurnResult:
        session = self.file_store.load_session(session_id)
        loaded = self.context_loader.load()
        memories = self.memory_store.recall(query=user_input, session_id=session_id)

        pre_context = RuntimeContext(
            session_id=session_id,
            user_input=user_input,
            messages=session.messages,
            memories=memories,
            active_skills=[],
            documents=loaded.documents,
            previous_response_id=session.last_response_id,
            loop_state=LoopState(max_iterations=self.halt_policy.max_iterations),
        )
        skills = self.skill_registry.resolve(pre_context)
        active_skill_names = [skill.name for skill in skills]
        ctx = pre_context.model_copy(update={"active_skills": active_skill_names})

        user_message = Message(role="user", content=user_input)
        session.messages.append(user_message)

        if user_input.strip() == "/stop":
            assistant_message = Message(role="assistant", content="Stopped current task.")
            session.messages.append(assistant_message)
            self.file_store.save_session(session)
            return TurnResult(
                session_id=session_id,
                reply=assistant_message.content,
                messages=session.messages,
            )

        tool_name, tool_result = self.tool_registry.try_execute_explicit_command(user_input=user_input, ctx=ctx)
        llm_response = None
        used_tools: list[str] = []
        iterations = 0
        if tool_result is not None:
            used_tools = [tool_name] if tool_name else []
            tool_message = Message(role="tool", name=tool_name, content=tool_result.content)
            assistant_message = Message(role="assistant", content=tool_result.content)
            session.messages.extend([tool_message, assistant_message])
            reply_text = tool_result.content
        else:
            system_prompts = [skill.build_prompt(ctx) for skill in skills]
            reply_text, llm_response, used_tools, loop_state = self.react_loop.run(ctx=ctx, system_prompts=system_prompts)
            iterations = loop_state.iteration
            session.messages.extend(loop_state.observations)
            assistant_message = Message(role="assistant", content=reply_text)
            session.messages.append(assistant_message)

        if llm_response is not None:
            session.last_response_id = llm_response.response_id

        consolidation = self.consolidator.maybe_consolidate(session)
        session.updated_at = datetime.now(timezone.utc)
        self.file_store.save_session(session)
        self.file_store.append_log(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": session_id,
                "user_input": user_input,
                "reply": reply_text,
                "used_skills": active_skill_names,
                "used_tools": used_tools,
                "llm_response": llm_response.model_dump(mode="json") if llm_response is not None else None,
                "consolidation": consolidation.model_dump(mode="json") if consolidation is not None else None,
            }
        )

        if self._should_persist_memory(user_input):
            self.memory_store.save_fact(text=user_input, source="user", tags=["captured"])

        return TurnResult(
            session_id=session_id,
            reply=reply_text,
            messages=session.messages,
            used_skills=active_skill_names,
            used_tools=used_tools,
            llm_response=llm_response,
            iterations=iterations,
            consolidation=consolidation,
        )

    @staticmethod
    def _should_persist_memory(user_input: str) -> bool:
        lowered = user_input.lower()
        return lowered.startswith("/remember ") or "remember" in lowered or "记住" in user_input

    def register_mcp_server(self, name: str, command: str) -> None:
        self.mcp_adapter.register_server(MCPServerSpec(name=name, command=command))
