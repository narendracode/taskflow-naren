import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { PlusIcon, FolderIcon, Trash2Icon } from "lucide-react";
import { useForm } from "react-hook-form";
import {
  useGetProjectsQuery,
  useCreateProjectMutation,
  useDeleteProjectMutation,
} from "@/features/projects/projectsApi";
import { useAppSelector } from "@/app/store";
import type { Project } from "@/types";
import { extractErrorMessage, formatDate } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter as DFooter,
} from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { EmptyState } from "@/components/EmptyState";

interface ProjectForm {
  name: string;
  description: string;
}

export function ProjectsPage() {
  const navigate = useNavigate();
  const currentUser = useAppSelector((s) => s.auth.user);
  const [createOpen, setCreateOpen] = useState(false);

  const { data, isLoading, error } = useGetProjectsQuery();
  const [createProject, { isLoading: creating }] = useCreateProjectMutation();
  const [deleteProject] = useDeleteProjectMutation();

  const { register, handleSubmit, reset, formState: { errors } } = useForm<ProjectForm>();

  const onCreateSubmit = async (values: ProjectForm) => {
    try {
      await createProject({
        name: values.name.trim(),
        description: values.description.trim() || undefined,
      }).unwrap();
      reset();
      setCreateOpen(false);
    } catch {
      // error surfaces in the form
    }
  };

  const handleDelete = async (e: React.MouseEvent, projectId: string) => {
    e.stopPropagation();
    if (!confirm("Delete this project and all its tasks?")) return;
    await deleteProject(projectId);
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Projects</h1>
          <p className="text-sm text-muted-foreground">
            Projects you own or are assigned tasks in
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <PlusIcon className="mr-1 h-4 w-4" />
          New Project
        </Button>
      </div>

      {/* States */}
      {isLoading && (
        <div className="flex justify-center py-20">
          <Spinner size="lg" />
        </div>
      )}

      {error && (
        <p className="rounded-md bg-destructive/10 p-4 text-sm text-destructive">
          {extractErrorMessage(error)}
        </p>
      )}

      {!isLoading && !error && data && data.data.length === 0 && (
        <EmptyState
          icon={FolderIcon}
          title="No projects yet"
          description="Create your first project to start tracking tasks."
          action={
            <Button onClick={() => setCreateOpen(true)}>
              <PlusIcon className="mr-1 h-4 w-4" />
              New Project
            </Button>
          }
        />
      )}

      {/* Project grid */}
      {data && data.data.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.data.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              isOwner={project.owner_id === currentUser?.id}
              onClick={() => navigate(`/projects/${project.id}`)}
              onDelete={(e) => handleDelete(e, project.id)}
            />
          ))}
        </div>
      )}

      {/* Create project dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Project</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit(onCreateSubmit)} className="grid gap-4">
            <div className="grid gap-1.5">
              <Label htmlFor="proj-name">
                Name <span className="text-destructive">*</span>
              </Label>
              <Input
                id="proj-name"
                placeholder="Project name"
                {...register("name", { required: "Name is required" })}
              />
              {errors.name && (
                <p className="text-xs text-destructive">{errors.name.message}</p>
              )}
            </div>

            <div className="grid gap-1.5">
              <Label htmlFor="proj-desc">Description</Label>
              <Textarea
                id="proj-desc"
                placeholder="What is this project about?"
                rows={3}
                {...register("description")}
              />
            </div>

            <DFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setCreateOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={creating}>
                {creating && <Spinner size="sm" className="mr-1" />}
                Create
              </Button>
            </DFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ── Project card sub-component ───────────────────────────────────────────────

interface ProjectCardProps {
  project: Project;
  isOwner: boolean;
  onClick: () => void;
  onDelete: (e: React.MouseEvent) => void;
}

function ProjectCard({ project, isOwner, onClick, onDelete }: ProjectCardProps) {
  return (
    <Card
      className="cursor-pointer transition-shadow hover:shadow-md"
      onClick={onClick}
    >
      <CardHeader>
        <CardTitle className="line-clamp-1">{project.name}</CardTitle>
        <CardDescription className="line-clamp-2 min-h-[2.5rem]">
          {project.description ?? <span className="italic text-muted-foreground/60">No description</span>}
        </CardDescription>
      </CardHeader>

      <CardFooter className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">
          Created {formatDate(project.created_at)}
        </span>
        {isOwner && (
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-muted-foreground hover:text-destructive"
            onClick={onDelete}
            title="Delete project"
          >
            <Trash2Icon className="h-4 w-4" />
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
