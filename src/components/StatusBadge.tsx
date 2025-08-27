import { Badge } from "@/components/ui/badge";
import { Clock, Check, X, CheckCircle } from "lucide-react";
import { CommentStatus } from "./CommentCard";

interface StatusBadgeProps {
  status: CommentStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const statusConfig = {
    pending: {
      label: 'Pending Review',
      className: 'bg-pending/10 text-pending hover:bg-pending/20 border-pending/20',
      icon: Clock
    },
    approved: {
      label: 'Approved',
      className: 'bg-success/10 text-success hover:bg-success/20 border-success/20',
      icon: Check
    },
    rejected: {
      label: 'Rejected',
      className: 'bg-destructive/10 text-destructive hover:bg-destructive/20 border-destructive/20',
      icon: X
    },
    posted: {
      label: 'Posted',
      className: 'bg-success/10 text-success hover:bg-success/20 border-success/20',
      icon: CheckCircle
    }
  };

  const config = statusConfig[status];
  const IconComponent = config.icon;

  return (
    <Badge variant="outline" className={config.className}>
      <IconComponent className="h-3 w-3 mr-1" />
      {config.label}
    </Badge>
  );
}