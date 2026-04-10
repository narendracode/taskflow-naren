import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { useAppSelector } from "@/app/store";
import {
  useCreateTaskMutation,
  useUpdateTaskMutation,
} from "@/features/tasks/tasksApi";
import { useSearchUsersQuery } from "@/features/users/usersApi";
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

  // Assignee search state
  const [assigneeSearch, setAssigneeSearch] = useState("");
  const [assigneeName, setAssigneeName] = useState("");
  const [showUserDropdown, setShowUserDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const { data: searchResults = [], isFetching: searchingUsers } =
    useSearchUsersQuery(assigneeSearch, {
      skip: assigneeSearch.length === 0,
    });

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
      // When editing, resolve the assignee name from search results or show current user
      if (task.assignee_id) {
        if (task.assignee_id === currentUser?.id) {
          setAssigneeName(currentUser.name);
        } else {
          // Will be resolved once search results load; for now show the id
          setAssigneeName(task.assignee_id);
          setAssigneeSearch(task.assignee_id);
        }
      } else {
        setAssigneeName("");
        setAssigneeSearch("");
      }
    } else {
      reset({
        title: "",
        description: "",
        status: "todo",
        priority: "medium",
        due_date: "",
        assignee_id: "",
      });
      setAssigneeName("");
      setAssigneeSearch("");
    }
    setShowUserDropdown(false);
  }, [task, reset, open, currentUser]);

  // When editing and search results resolve, update display name
  useEffect(() => {
    if (searchResults.length > 0 && task?.assignee_id) {
      const match = searchResults.find((u) => u.id === task.assignee_id);
      if (match) {
        setAssigneeName(match.name);
        setAssigneeSearch("");
      }
    }
  }, [searchResults, task?.assignee_id]);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setShowUserDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

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
              <Label htmlFor="assignee_search">Assignee</Label>
              <div className="relative" ref={dropdownRef}>
                <div className="flex gap-1.5">
                  <Input
                    id="assignee_search"
                    placeholder="Search by name…"
                    value={showUserDropdown ? assigneeSearch : assigneeName}
                    onChange={(e) => {
                      setAssigneeSearch(e.target.value);
                      setShowUserDropdown(true);
                      if (!e.target.value) {
                        setValue("assignee_id", "");
                        setAssigneeName("");
                      }
                    }}
                    onFocus={() => {
                      setShowUserDropdown(true);
                      setAssigneeSearch(assigneeName);
                    }}
                    autoComplete="off"
                    className="flex-1"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="shrink-0 text-xs"
                    title="Assign to me"
                    onClick={() => {
                      setValue("assignee_id", currentUser?.id ?? "");
                      setAssigneeName(currentUser?.name ?? "");
                      setAssigneeSearch("");
                      setShowUserDropdown(false);
                    }}
                  >
                    Me
                  </Button>
                  {assigneeName && (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="shrink-0 text-xs"
                      title="Clear assignee"
                      onClick={() => {
                        setValue("assignee_id", "");
                        setAssigneeName("");
                        setAssigneeSearch("");
                        setShowUserDropdown(false);
                      }}
                    >
                      ✕
                    </Button>
                  )}
                </div>
                {showUserDropdown && assigneeSearch.length > 0 && (
                  <div className="absolute z-50 mt-1 max-h-48 w-full overflow-auto rounded-md border bg-popover p-1 shadow-md">
                    {searchingUsers && (
                      <div className="flex items-center gap-2 px-2 py-1.5 text-sm text-muted-foreground">
                        <Spinner size="sm" /> Searching…
                      </div>
                    )}
                    {!searchingUsers && searchResults.length === 0 && (
                      <div className="px-2 py-1.5 text-sm text-muted-foreground">
                        No users found
                      </div>
                    )}
                    {searchResults.map((user) => (
                      <button
                        key={user.id}
                        type="button"
                        className="flex w-full flex-col items-start rounded-sm px-2 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground"
                        onClick={() => {
                          setValue("assignee_id", user.id);
                          setAssigneeName(user.name);
                          setAssigneeSearch("");
                          setShowUserDropdown(false);
                        }}
                      >
                        <span className="font-medium">{user.name}</span>
                        <span className="text-xs text-muted-foreground">
                          {user.email}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
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

