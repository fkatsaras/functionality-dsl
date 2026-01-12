<script lang="ts">
    import UnauthorizedState from "$lib/primitives/icons/UnauthorizedState.svelte";

    const props = $props<{
        requiredRoles?: string[];
        operation?: string;
        message?: string;
    }>();

    const displayMessage = $derived(
        props.message ||
        (props.requiredRoles && props.requiredRoles.length > 0
            ? `Requires ${props.operation || 'access'} permission with one of: ${props.requiredRoles.join(", ")}`
            : "Access denied")
    );
</script>

<UnauthorizedState message={displayMessage} />
