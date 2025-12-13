<script>
    const { class: className = "", fullWidth = false } = $props();
</script>

<div class={`card ${className} ${fullWidth ? 'card-fullwidth' : ''}`}>

    <div class="card-header">
        <slot name="header" />
    </div>

    <div class="card-body">
        <slot /> <!--  default slot-->
        <slot name="children" />
    </div>

    <div class="card-footer">
        <slot name="footer" />
    </div>

</div>