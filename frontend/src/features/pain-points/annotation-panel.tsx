import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { addAnnotation } from "../../api";
import { ErrorState } from "../../components/query-state";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Field } from "../../components/ui/field";
import { Select } from "../../components/ui/select";
import { Textarea } from "../../components/ui/textarea";
import { errorMessage } from "../../lib/errors";

const schema = z.object({
  annotationType: z.enum(["root_cause", "interview", "next_step", "general"]),
  content: z.string().trim().min(2, "批注至少 2 个字符。").max(5_000),
});

type Values = z.infer<typeof schema>;

export function AnnotationPanel({ painPointId }: { painPointId: string }) {
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { annotationType: "general", content: "" },
  });
  const annotation = useMutation({
    mutationFn: (values: Values) =>
      addAnnotation(painPointId, {
        annotation_type: values.annotationType,
        content: values.content,
      }),
    onSuccess: () => form.reset({ annotationType: "general", content: "" }),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>研究批注</CardTitle>
      </CardHeader>
      <CardContent>
        {annotation.isError ? <ErrorState message={errorMessage(annotation.error)} className="mb-3" /> : null}
        <form className="space-y-3" onSubmit={form.handleSubmit((values) => annotation.mutate(values))}>
          <Field id="annotation-type" label="批注类型">
            <Select id="annotation-type" {...form.register("annotationType")}>
              <option value="general">一般说明</option>
              <option value="root_cause">根因假设</option>
              <option value="interview">访谈记录</option>
              <option value="next_step">下一步计划</option>
            </Select>
          </Field>
          <Field
            id="annotation-content"
            label="批注内容"
            required
            error={form.formState.errors.content?.message}
          >
            <Textarea id="annotation-content" {...form.register("content")} />
          </Field>
          <Button type="submit" variant="secondary" className="w-full" disabled={annotation.isPending}>
            保存批注
          </Button>
          {annotation.isSuccess ? (
            <p className="text-xs font-medium text-emerald-700" role="status">批注已保存。</p>
          ) : null}
        </form>
      </CardContent>
    </Card>
  );
}
