import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ShieldCheck, XCircle } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { rejectPainPoint, verifyPainPoint } from "../../api";
import { queryKeys } from "../../api/query-keys";
import { ErrorState } from "../../components/query-state";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Field } from "../../components/ui/field";
import { Textarea } from "../../components/ui/textarea";
import { errorMessage } from "../../lib/errors";

const verifySchema = z.object({ reason: z.string().max(2_000) });
const rejectSchema = z.object({
  reason: z.string().trim().min(3, "拒绝时必须填写至少 3 个字符的原因。").max(2_000),
});

type VerifyValues = z.infer<typeof verifySchema>;
type RejectValues = z.infer<typeof rejectSchema>;

export function ReviewPanel({ painPointId }: { painPointId: string }) {
  const queryClient = useQueryClient();
  const invalidate = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.painPoint(painPointId) }),
      queryClient.invalidateQueries({ queryKey: ["pain-points"] }),
    ]);
  };
  const verify = useMutation({
    mutationFn: (values: VerifyValues) => verifyPainPoint(painPointId, values.reason),
    onSuccess: () => {
      verifyForm.reset();
      return invalidate();
    },
  });
  const reject = useMutation({
    mutationFn: (values: RejectValues) => rejectPainPoint(painPointId, values.reason),
    onSuccess: () => {
      rejectForm.reset();
      return invalidate();
    },
  });
  const verifyForm = useForm<VerifyValues>({
    resolver: zodResolver(verifySchema),
    defaultValues: { reason: "" },
  });
  const rejectForm = useForm<RejectValues>({
    resolver: zodResolver(rejectSchema),
    defaultValues: { reason: "" },
  });
  const mutationError = verify.error ?? reject.error;

  return (
    <Card>
      <CardHeader>
        <CardTitle>人工复核</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        {mutationError ? <ErrorState message={errorMessage(mutationError)} /> : null}
        <form
          className="space-y-3"
          onSubmit={verifyForm.handleSubmit((values) => verify.mutate(values))}
        >
          <Field
            id="verify-reason"
            label="核验说明"
            hint="确认已打开来源并逐字核对引用。"
            error={verifyForm.formState.errors.reason?.message}
          >
            <Textarea id="verify-reason" {...verifyForm.register("reason")} />
          </Field>
          <Button type="submit" className="w-full" disabled={verify.isPending}>
            <ShieldCheck className="size-4" aria-hidden="true" />
            人工核验为已确认
          </Button>
        </form>

        <form
          className="space-y-3 border-t border-line pt-5"
          onSubmit={rejectForm.handleSubmit((values) => reject.mutate(values))}
        >
          <Field
            id="reject-reason"
            label="拒绝原因"
            required
            error={rejectForm.formState.errors.reason?.message}
          >
            <Textarea id="reject-reason" {...rejectForm.register("reason")} />
          </Field>
          <Button type="submit" variant="danger" className="w-full" disabled={reject.isPending}>
            <XCircle className="size-4" aria-hidden="true" />
            标记为不成立
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
