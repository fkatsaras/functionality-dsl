<script lang="ts">
    const {
        status = "",
        class: className = ""
    } = $props<{
        status?: string;
        class?: string;
    }>();

    // Map status to color scheme
    const statusStyles: Record<string, string> = {
        pending: "bg-[var(--surface)] text-yellow-400 border-yellow-600/50",
        assigned: "bg-blue-950/50 text-blue-400 border-blue-600/50",
        picked_up: "bg-purple-950/50 text-purple-400 border-purple-600/50",
        in_transit: "bg-indigo-950/50 text-indigo-400 border-indigo-600/50",
        delivered: "bg-[var(--green-tint)] text-[var(--green-text)] border-green-600/50",
        cancelled: "bg-[var(--red-tint)] text-[var(--red-text)] border-red-600/50",
        active: "bg-[var(--green-tint)] text-[var(--green-text)] border-green-600/50",
        inactive: "bg-[var(--surface)] text-[var(--text-muted)] border-[var(--edge)]",
    };

    const statusLabels: Record<string, string> = {
        pending: "Pending",
        assigned: "Assigned",
        picked_up: "Picked Up",
        in_transit: "In Transit",
        delivered: "Delivered",
        cancelled: "Cancelled",
        active: "Active",
        inactive: "Inactive",
    };

    const normalizedStatus = status.toLowerCase().replace(/\s+/g, "_");
    const colorClass = statusStyles[normalizedStatus] || "bg-[var(--surface)] text-[var(--text-muted)] border-[var(--edge)]";
    const label = statusLabels[normalizedStatus] || status;
</script>

<span class={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border ${colorClass} ${className}`}>
    <span class="w-1.5 h-1.5 rounded-full" style="background-color: currentColor; opacity: 0.8;"></span>
    {label}
</span>
