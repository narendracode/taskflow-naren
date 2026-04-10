import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { useAppSelector } from "@/app/store";
import {
  useCreateTaskMutation,
  useUpdateTaskMutation,
} from "@/features/tasks/tasksApi";
import type { Task, TaskPriority, TaskStatus } from "@/types";
import { extractErrorMessage } from "@/lib/utils";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "./ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { Spinner } from "./ui/spinner";

interface TaskFormValues {
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  due_date: string;
  assignee_id: string;
}

interface TaskModalProps {
  open: boolean;
  onClose: () => void;
  projectId: string;
  task?: Task; // if provided → edit mode
}

export function TaskModal({ open, onClose, projectId, task }: TaskModalProps) {
  const currentUser = useAppSelector((s) => s.auth.user);
  const isEdit = !!task;

  const [createTask, { isLoading: creating, error: createError }] =
    useCreateTaskMutation();
  const [updateTask, { isLoading: updating, error: updateError }] =
    useUpdateTaskMutation();

  const isLoading = creating || updating;
  const apiError = createError ?? updateError;

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<TaskFormValues>({
    defaultValues: {
      title: "",
      description: "",
      status: "todo",
      priority: "medium",
      due_date: "",
      assignee_id: "",
    },
  });

  // Populate form when editing an existing task
  useEffect(() => {
    if (task) {
      reset({
        title: task.title,
        description: task.description ?? "",
        status: task.status,
        priority: task.priority,
        due_date: task.due_date ?? "",
        assignee_id: task.assignee_id ?? "",
      });
    } else {
      reset({
        title: "",
        description: "",
        status: "todo",
        priority: "medium",
        due_date: "",
        assignee_id: "",
      });
    }
  }, [task, reset, open]);

  const onSubmit = async (values: TaskFormValues) => {
    const payload = {
      title: values.title.trim(),
      description: values.description.trim() || undefined,
      status: values.status,
      priority: values.priority,
      due_date: values.due_date || null,
      assignee_id: values.assignee_id.trim() || null,
    };

    try {
      if (isEdit) {
        await updateTask({
          taskId: task!.id,
          projectId,
          ...payload,
        }).unwrap();
      } else {
        await createTask({ projectId, ...payload }).unwrap();
      }
      onClose();
    } catch {
      // error shown via apiError
    }
  };

  const statusValue = watch("status");
  const priorityValue = watch("priority");

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit Task" : "New Task"}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4 py-2">
          {/* Title */}
          <div className="grid gap-1.5">
            <Label htmlFor="title">
              Title <span className="text-destructive">*</span>
            </Label>
            <Input
              id="title"
              placeholder="Task title"
              {...register("title", { required: "Title is required" })}
            />
            {errors.title && (
              <p className="text-xs text-destructive">{errors.title.message}</p>
            )}
          </div>

          {/* Description */}
          <div className="grid gap-1.5">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              placeholder="Optional details…"
              rows={3}
              {...register("description")}
            />
          </div>

          {/* Status & Priority */}
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label>Status</Label>
              <Select
                value={statusValue}
                onValueChange={(v) => setValue("status", v as TaskStatus)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="todo">Todo</SelectItem>
                  <SelectItem value="in_progress">In Progress</SelectItem>
                  <SelectItem value="done">Done</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-1.5">
              <Label>Priority</Label>
              <Select
                value={priorityValue}
                onValueChange={(v) => setValue("priority", v as TaskPriority)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Due date & Assignee */}
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="due_date">Due Date</Label>
              <Input id="due_date" type="date" {...register("due_date")} />
            </div>

            <div className="grid gap-1.5">
              <Label htmlFor="assignee_id">Assignee ID</Label>
              <div className="flex gap-1.5">
                <Input
                  id="assignee_id"
                  placeholder="User UUID"
                  {...register("assignee_id")}
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="shrink-0 text-xs"
                  title="Assign to me"
                  onClick={() =>
                    setValue("assignee_id", currentUser?.id ?? "")
                  }
                >
                  Me
                </Button>
              </div>
            </div>
          </div>

          {/* API error */}
          {apiError && (
            <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {extractErrorMessage(apiError)}
            </p>
          )}

          <DialogFooter className="mt-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading && <Spinner size="sm" className="mr-1" />}
              {isEdit ? "Save Changes" : "Create Task"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

