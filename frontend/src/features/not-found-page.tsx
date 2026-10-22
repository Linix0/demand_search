import { Link } from "react-router";

import { PageHeader } from "../components/page-header";
import { Button } from "../components/ui/button";

export function NotFoundPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="页面不存在" description="当前地址没有对应的研究页面。" />
      <Link to="/">
        <Button>返回概览</Button>
      </Link>
    </div>
  );
}
