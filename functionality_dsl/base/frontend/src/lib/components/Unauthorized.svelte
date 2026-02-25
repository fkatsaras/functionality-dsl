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
        props.message || "You do not have permission to view this"
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
