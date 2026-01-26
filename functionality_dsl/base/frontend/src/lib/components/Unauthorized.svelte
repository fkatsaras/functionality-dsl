<script lang="ts">
    import Card from "$lib/primitives/Card.svelte";
    import UnauthorizedState from "$lib/primitives/icons/UnauthorizedState.svelte";

    const props = $props<{
        requiredRoles?: string[];
        operation?: string;
        message?: string;
        title?: string;
    }>();

    const displayMessage = $derived(
        props.message ||
        (props.requiredRoles && props.requiredRoles.length > 0
            ? `Requires ${props.operation || 'access'} permission with one of: ${props.requiredRoles.join(", ")}`
            : "Access denied")
    );
</script>

{#if props.title}
    <Card>
        <svelte:fragment slot="header">
            <span>{props.title}</span>
        </svelte:fragment>
        <svelte:fragment slot="children">
            <UnauthorizedState message={displayMessage} />
        </svelte:fragment>
    </Card>
{:else}
    <UnauthorizedState message={displayMessage} />
{/if}
