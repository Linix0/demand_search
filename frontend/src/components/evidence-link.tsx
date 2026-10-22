import { ExternalLink } from "lucide-react";

import { isHttpUrl } from "../lib/utils";

export function EvidenceLink({
  url,
  label = "打开原始来源",
  className,
}: {
  url: string | null | undefined;
  label?: string;
  className?: string;
}) {
  if (!isHttpUrl(url)) {
    return (
      <span className={className} role="status">
        来源地址缺失或不是有效的 HTTP(S) 链接
      </span>
    );
  }
  return (
    <a
      className={className}
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      referrerPolicy="no-referrer"
    >
      {label}
      <ExternalLink className="ml-1 inline size-3.5" aria-hidden="true" />
    </a>
  );
}
