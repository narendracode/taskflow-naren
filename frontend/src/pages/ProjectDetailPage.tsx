import { useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  DragDropContext,
  Droppable,
  Draggable,
  type DropResult,
  type DraggableProvidedDragHandleProps,
} from "@hello-pangea/dnd";
import {
  ArrowLeftIcon,
  PlusIcon,
  ClipboardListIcon,
  CalendarIcon,
  UserIcon,
  Trash2Icon,
  PencilIcon,
  GripVerticalIcon,
} from "lucide-react";
import { useGetProjectQuery } from "@/features/projects/projectsApi";
import {
  useGetProjectTasksQuery,
  useUpdateTaskMutation,
  useDeleteTaskMutation,
} from "@/features/tasks/tasksApi";
import { useAppSelector } from "@/app/store";
import { useProjectSSE } from "@/hooks/useProjectSSE";
import type { Task, TaskStatus, TaskPriority } from "@/types";
import { formatDate, extractErrorMessage, cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { EmptyState } from "@/components/EmptyState";
import { TaskModal } from "@/components/TaskModal";
import { ConfirmDialog } from "@/components/ConfirmDialog";

// ── Column config ─────────────────────────────────────────────────────────────

const COLUMNS: { status: TaskStatus; label: string; color: string }[] = [
  { status: "todo", label: "Todo", color: "bg-slate-100 dark:bg-slate-800/50" },
  { status: "in_progress", label: "In Progress", color: "bg-blue-50 dark:bg-blue-950/40" },
  { status: "done", label: "Done", color: "bg-green-50 dark:bg-green-950/40" },
];

const STATUS_LABELS: Record<TaskStatus, string> = {
  todo: "Todo",
  in_progress: "In Progress",
  done: "Done",
};

const PRIORITY_LABELS: Record<TaskPriority, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
};

// ── Page ──────────────────────────────────────────────────────────────────────

export function ProjectDetailPage() {
  const { id: projectId = "" } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const currentUser = useAppSelector((s) => s.auth.user);

  // Filters
  const [statusFilter, setStatusFilter] = useState<TaskStatus | "all">("all");
  const [taskModalOpen, setTaskModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | undefined>();
  const [deleteTaskId, setDeleteTaskId] = useState<string | null>(null);

  const { data: project, isLoading: projectLoading, error: projectError } =
    useGetProjectQuery(projectId, { skip: !projectId });

  // Real-time updates via SSE — keeps other tabs/devices in sync
  useProjectSSE(projectId || undefined);

  const queryArgs = {
    projectId,
    ...(statusFilter !== "all" ? { status: statusFilter } : {}),
  };

  const { data: tasksData, isLoading: tasksLoading, error: tasksError } =
    useGetProjectTasksQuery(queryArgs, { skip: !projectId });

  const [updateTask] = useUpdateTaskMutation();
  const [deleteTask] = useDeleteTaskMutation();

  const isOwner = project?.owner_id === currentUser?.id;

  const openCreate = () => {
    setEditingTask(undefined);
    setTaskModalOpen(true);
  };

  const openEdit = (task: Task) => {
    setEditingTask(task);
    setTaskModalOpen(true);
  };

  const handleStatusChange = (task: Task, newStatus: TaskStatus) => {
    updateTask({ taskId: task.id, projectId, status: newStatus });
  };

  // Group tasks by status for Kanban columns
  const tasks = tasksData?.data ?? [];
  const byStatus = (status: TaskStatus) =>
    tasks.filter((t) => t.status === status);

  const onDragEnd = useCallback(
    (result: DropResult) => {
      const { destination, source, draggableId } = result;
      if (!destination) return;
      if (destination.droppableId === source.droppableId) return;

      const newStatus = destination.droppableId as TaskStatus;
      const task = tasks.find((t) => t.id === draggableId);
      if (task && task.status !== newStatus) {
        handleStatusChange(task, newStatus);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [tasks, projectId]
  );

  const handleDeleteClick = (taskId: string) => {
    setDeleteTaskId(taskId);
  };

  const confirmDeleteTask = async () => {
    if (deleteTaskId) {
      await deleteTask({ taskId: deleteTaskId, projectId });
      setDeleteTaskId(null);
    }
  };

  // ── Loading / error ──────────────────────────────────────────────────────

  if (projectLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (projectError || !project) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        <p className="text-destructive">
          {extractErrorMessage(projectError) || "Project not found"}
        </p>
        <Button variant="link" onClick={() => navigate("/projects")}>
          ← Back to Projects
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      {/* Header */}
      <div className="mb-6">
        <Button
          variant="ghost"
          size="sm"
          className="mb-2 -ml-2 text-muted-foreground"
          onClick={() => navigate("/projects")}
        >
          <ArrowLeftIcon className="mr-1 h-4 w-4" />
          Projects
        </Button>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold">{project.name}</h1>
            {project.description && (
              <p className="mt-1 text-sm text-muted-foreground">
                {project.description}
              </p>
            )}
          </div>
          <Button onClick={openCreate} className="shrink-0">
            <PlusIcon className="mr-1 h-4 w-4" />
            Add Task
          </Button>
        </div>
      </div>

      {/* Filter bar */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Status:</span>
          <Select
            value={statusFilter}
            onValueChange={(v) => setStatusFilter(v as TaskStatus | "all")}
          >
            <SelectTrigger className="h-8 w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="todo">Todo</SelectItem>
              <SelectItem value="in_progress">In Progress</SelectItem>
              <SelectItem value="done">Done</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {tasksData && (
          <span className="text-sm text-muted-foreground">
            {tasksData.total} task{tasksData.total !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Tasks loading / error */}
      {tasksLoading && (
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      )}

      {tasksError && (
        <p className="text-sm text-destructive">{extractErrorMessage(tasksError)}</p>
      )}

      {/* ── Kanban board (desktop) / list (mobile) ── */}
      {!tasksLoading && !tasksError && (
        <>
          {tasks.length === 0 ? (
            <EmptyState
              icon={ClipboardListIcon}
              title="No tasks yet"
              description={
                statusFilter !== "all"
                  ? `No tasks with status "${STATUS_LABELS[statusFilter]}".`
                  : "Create your first task to get started."
              }
              action={
                <Button onClick={openCreate}>
                  <PlusIcon className="mr-1 h-4 w-4" />
                  Add Task
                </Button>
              }
            />
          ) : (
            <>
              {/* Kanban — visible on md+ */}
              <DragDropContext onDragEnd={onDragEnd}>
                <div className="hidden gap-4 md:grid md:grid-cols-3">
                  {COLUMNS.map(({ status, label, color }) => {
                    const col = statusFilter === "all"
                      ? byStatus(status)
                      : status === statusFilter
                      ? tasks
                      : [];
                    if (statusFilter !== "all" && status !== statusFilter) return null;
                    return (
                      <KanbanColumn
                        key={status}
                        status={status}
                        label={label}
                        color={color}
                        tasks={col}
                        isOwner={isOwner}
                        projectId={projectId}
                        onEdit={openEdit}
                        onStatusChange={handleStatusChange}
                        onDelete={handleDeleteClick}
                      />
                    );
                  })}
                </div>
              </DragDropContext>

              {/* Flat list — visible on mobile */}
              <ul className="grid gap-3 md:hidden">
                {tasks.map((task) => (
                  <TaskListItem
                    key={task.id}
                    task={task}
                    isOwner={isOwner}
                    projectId={projectId}
                    onEdit={() => openEdit(task)}
                    onStatusChange={(s) => handleStatusChange(task, s)}
                    onDelete={() => handleDeleteClick(task.id)}
                  />
                ))}
              </ul>
            </>
          )}
        </>
      )}

      {/* Delete task confirmation */}
      <ConfirmDialog
        open={deleteTaskId !== null}
        title="Delete Task"
        description="This will permanently delete this task. This action cannot be undone."
        onConfirm={confirmDeleteTask}
        onCancel={() => setDeleteTaskId(null)}
      />

      {/* Task create/edit modal */}
      <TaskModal
        open={taskModalOpen}
        onClose={() => setTaskModalOpen(false)}
        projectId={projectId}
        task={editingTask}
      />
    </div>
  );
}

// ── Kanban Column ─────────────────────────────────────────────────────────────

interface ColumnProps {
  status: TaskStatus;
  label: string;
  color: string;
  tasks: Task[];
  isOwner: boolean;
  projectId: string;
  onEdit: (task: Task) => void;
  onStatusChange: (task: Task, status: TaskStatus) => void;
  onDelete: (taskId: string) => void;
}

function KanbanColumn({
  status,
  label,
  color,
  tasks,
  isOwner,
  onEdit,
  onStatusChange,
  onDelete,
}: ColumnProps) {
  return (
    <Droppable droppableId={status}>
      {(provided, snapshot) => (
        <div
          ref={provided.innerRef}
          {...provided.droppableProps}
          className={cn(
            "rounded-xl p-3 transition-colors",
            color,
            snapshot.isDraggingOver && "ring-2 ring-primary/40"
          )}
        >
          <div className="mb-3 flex items-center gap-2">
            <span className="text-sm font-semibold">{label}</span>
            <span className="rounded-full bg-white/70 dark:bg-white/10 px-2 py-0.5 text-xs font-medium">
              {tasks.length}
            </span>
          </div>
          <div className="flex flex-col gap-2">
            {tasks.map((task, index) => (
              <Draggable key={task.id} draggableId={task.id} index={index}>
                {(dragProvided, dragSnapshot) => (
                  <div
                    ref={dragProvided.innerRef}
                    {...dragProvided.draggableProps}
                  >
                    <TaskCard
                      task={task}
                      isOwner={isOwner}
                      onEdit={() => onEdit(task)}
                      onStatusChange={(s) => onStatusChange(task, s)}
                      onDelete={() => onDelete(task.id)}
                      isDragging={dragSnapshot.isDragging}
                      dragHandleProps={dragProvided.dragHandleProps}
                    />
                  </div>
                )}
              </Draggable>
            ))}
            {provided.placeholder}
            {tasks.length === 0 && (
              <p className="py-6 text-center text-xs text-muted-foreground">
                No tasks
              </p>
            )}
          </div>
        </div>
      )}
    </Droppable>
  );
}

// ── Task Card ─────────────────────────────────────────────────────────────────

interface TaskCardProps {
  task: Task;
  isOwner: boolean;
  onEdit: () => void;
  onStatusChange: (status: TaskStatus) => void;
  onDelete: () => void;
  isDragging?: boolean;
  dragHandleProps?: DraggableProvidedDragHandleProps | null;
}

function TaskCard({ task, isOwner, onEdit, onStatusChange, onDelete, isDragging, dragHandleProps }: TaskCardProps) {
  return (
    <div className={cn(
      "rounded-lg border bg-card text-card-foreground p-3 shadow-sm transition-shadow",
      isDragging && "shadow-lg ring-2 ring-primary/30"
    )}>
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="flex items-start gap-1.5 min-w-0">
          <span
            {...dragHandleProps}
            className="mt-0.5 shrink-0 cursor-grab text-muted-foreground/50 hover:text-muted-foreground active:cursor-grabbing"
          >
            <GripVerticalIcon className="h-4 w-4" />
          </span>
          <p
            className="cursor-pointer text-sm font-medium leading-snug hover:text-primary"
            onClick={onEdit}
          >
            {task.title}
          </p>
        </div>
        <div className="flex shrink-0 gap-1">
          <button
            onClick={onEdit}
            className="text-muted-foreground hover:text-foreground"
            title="Edit task"
          >
            <PencilIcon className="h-3.5 w-3.5" />
          </button>
          {isOwner && (
            <button
              onClick={onDelete}
              className="text-muted-foreground hover:text-destructive"
              title="Delete task"
            >
              <Trash2Icon className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Priority + due date */}
      <div className="mb-2 flex flex-wrap items-center gap-1.5">
        <Badge variant={task.priority as TaskPriority}>
          {PRIORITY_LABELS[task.priority]}
        </Badge>
        {task.due_date && (
          <span className="flex items-center gap-0.5 text-xs text-muted-foreground">
            <CalendarIcon className="h-3 w-3" />
            {formatDate(task.due_date)}
          </span>
        )}
        {task.assignee_id && (
          <span className="flex items-center gap-0.5 text-xs text-muted-foreground">
            <UserIcon className="h-3 w-3" />
            assigned
          </span>
        )}
      </div>

      {/* Inline status change — this is the optimistic update trigger */}
      <Select value={task.status} onValueChange={(v) => onStatusChange(v as TaskStatus)}>
        <SelectTrigger className="h-7 text-xs">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="todo">Todo</SelectItem>
          <SelectItem value="in_progress">In Progress</SelectItem>
          <SelectItem value="done">Done</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}

// ── Task List Item (mobile) ───────────────────────────────────────────────────

interface TaskListItemProps {
  task: Task;
  isOwner: boolean;
  projectId: string;
  onEdit: () => void;
  onStatusChange: (status: TaskStatus) => void;
  onDelete: () => void;
}

function TaskListItem({
  task,
  isOwner,
  onEdit,
  onStatusChange,
  onDelete,
}: TaskListItemProps) {
  return (
    <li className="flex items-start gap-3 rounded-lg border bg-card p-3 shadow-sm">
      <div className="flex-1 min-w-0">
        <p
          className="cursor-pointer font-medium leading-snug hover:text-primary"
          onClick={onEdit}
        >
          {task.title}
        </p>
        <div className="mt-1 flex flex-wrap items-center gap-1.5">
          <Badge variant={task.status}>{STATUS_LABELS[task.status]}</Badge>
          <Badge variant={task.priority}>{PRIORITY_LABELS[task.priority]}</Badge>
          {task.due_date && (
            <span className="text-xs text-muted-foreground">
              Due {formatDate(task.due_date)}
            </span>
          )}
        </div>
        {/* Status quick-change */}
        <div className="mt-2">
          <Select value={task.status} onValueChange={(v) => onStatusChange(v as TaskStatus)}>
            <SelectTrigger className="h-7 w-36 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="todo">Todo</SelectItem>
              <SelectItem value="in_progress">In Progress</SelectItem>
              <SelectItem value="done">Done</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex shrink-0 flex-col gap-1">
        <button onClick={onEdit} className="text-muted-foreground hover:text-foreground">
          <PencilIcon className="h-4 w-4" />
        </button>
        {isOwner && (
          <button onClick={onDelete} className="text-muted-foreground hover:text-destructive">
            <Trash2Icon className="h-4 w-4" />
          </button>
        )}
      </div>
    </li>
  );
}
