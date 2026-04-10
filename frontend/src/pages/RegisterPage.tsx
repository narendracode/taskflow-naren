import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { useAppDispatch, useAppSelector } from "@/app/store";
import { setCredentials } from "@/features/auth/authSlice";
import { useRegisterMutation } from "@/features/auth/authApi";
import { extractErrorMessage, extractFieldErrors } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";

interface RegisterForm {
  name: string;
  email: string;
  password: string;
}

export function RegisterPage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const isAuthenticated = useAppSelector((s) => s.auth.isAuthenticated);

  const [register_, { isLoading, error }] = useRegisterMutation();

  useEffect(() => {
    if (isAuthenticated) navigate("/projects", { replace: true });
  }, [isAuthenticated, navigate]);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<RegisterForm>();

  const onSubmit = async (values: RegisterForm) => {
    try {
      const result = await register_(values).unwrap();
      dispatch(setCredentials({ user: result.user, token: result.access_token }));
      navigate("/projects", { replace: true });
    } catch (err) {
      const fields = extractFieldErrors(err);
      if (fields) {
        Object.entries(fields).forEach(([k, v]) =>
          setError(k as keyof RegisterForm, { message: v })
        );
      }
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40 px-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Create account</CardTitle>
          <p className="text-sm text-muted-foreground">Get started with TaskFlow</p>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4">
            <div className="grid gap-1.5">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                placeholder="Your full name"
                autoComplete="name"
                {...register("name", { required: "Name is required" })}
              />
              {errors.name && (
                <p className="text-xs text-destructive">{errors.name.message}</p>
              )}
            </div>

            <div className="grid gap-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                autoComplete="email"
                {...register("email", { required: "Email is required" })}
              />
              {errors.email && (
                <p className="text-xs text-destructive">{errors.email.message}</p>
              )}
            </div>

            <div className="grid gap-1.5">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Min. 8 chars, 1 uppercase, 1 digit"
                autoComplete="new-password"
                {...register("password", {
                  required: "Password is required",
                  minLength: { value: 8, message: "Must be at least 8 characters" },
                })}
              />
              {errors.password && (
                <p className="text-xs text-destructive">{errors.password.message}</p>
              )}
            </div>

            {error && !extractFieldErrors(error) && (
              <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {extractErrorMessage(error)}
              </p>
            )}

            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading && <Spinner size="sm" className="mr-2" />}
              Create Account
            </Button>
          </form>

          <p className="mt-4 text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link to="/login" className="text-primary underline-offset-4 hover:underline">
              Sign in
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
