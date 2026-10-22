import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { GitMerge } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { mergePainPoint } from "../../api";
import { queryKeys } from "../../api/query-keys";
import { ErrorState } from "../../components/query-state";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Field } from "../../components/ui/field";
import { Input } from "../../components/ui/input";
import { errorMessage } from "../../lib/errors";

const schema = z.object({
  targetPainPointId: z.string().uuid("请输入有效的目标痛点 UUID。"),
  reason: z.string().max(2_000),
});

type Values = z.infer<typeof schema>;

export function MergePanel({ painPointId }: { painPointId: string }) {
  const queryClient = useQueryClient();
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { targetPainPointId: "", reason: "" },
  });
  const merge = useMutation({
    mutationFn: (values: Values) =>
      mergePainPoint(painPointId, values.targetPainPointId, values.reason),
    onSuccess: async () => {
      form.reset();
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.painPoint(painPointId) }),
        queryClient.invalidateQueries({ queryKey: ["pain-points"] }),
      ]);
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>合并重复痛点</CardTitle>
      </CardHeader>
      <CardContent>
        {merge.isError ? <ErrorState message={errorMessage(merge.error)} className="mb-3" /> : null}
        <form className="space-y-3" onSubmit={form.handleSubmit((values) => merge.mutate(values))}>
          <Field
            id="merge-target"
            label="目标痛点 UUID"
            required
            error={form.formState.errors.targetPainPointId?.message}
          >
            <Input id="merge-target" {...form.register("targetPainPointId")} />
          </Field>
          <Field id="merge-reason" label="合并原因">
            <Input id="merge-reason" {...form.register("reason")} />
          </Field>
          <Button type="submit" variant="secondary" className="w-full" disabled={merge.isPending}>
            <GitMerge className="size-4" aria-hidden="true" />
            合并并保留全部证据
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
