<script>
    const { class: className = "" } = $props();
</script>

<div class={`card ${className}`}>
    
    <div class="card-header">
        <slot name="header" />
    </div>

    <div class="card-body">
        <slot name="children" />
    </div>

    <div class="card-footer">
        <slot name="footer" />
    </div>

</div>