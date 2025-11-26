<script lang="ts">
    let {
        file = $bindable(null),
        accept = "*",
        maxSize = 52428800, // 50MB default
        class: className = "",
        placeholder = "Drop a file here or click to browse"
    } = $props<{
        file: File | null;
        accept?: string;
        maxSize?: number;
        class?: string;
        placeholder?: string;
    }>();

    let isDragging = $state(false);
    let uploadProgress = $state(0);
    let isUploading = $state(false);
    let error = $state<string | null>(null);
    let fileInputElement: HTMLInputElement;

    function handleDragOver(e: DragEvent) {
        e.preventDefault();
        isDragging = true;
    }

    function handleDragLeave(e: DragEvent) {
        e.preventDefault();
        isDragging = false;
    }

    function handleDrop(e: DragEvent) {
        e.preventDefault();
        isDragging = false;

        const files = e.dataTransfer?.files;
        if (files && files.length > 0) {
            processFile(files[0]);
        }
    }

    function handleFileSelect(e: Event) {
        const target = e.target as HTMLInputElement;
        const files = target.files;
        if (files && files.length > 0) {
            processFile(files[0]);
        }
    }

    function processFile(selectedFile: File) {
        error = null;

        // Validate file size
        if (selectedFile.size > maxSize) {
            error = `File too large. Max size: ${(maxSize / 1048576).toFixed(0)}MB`;
            return;
        }

        // Simulate upload progress
        isUploading = true;
        uploadProgress = 0;

        const interval = setInterval(() => {
            uploadProgress += 10;
            if (uploadProgress >= 100) {
                clearInterval(interval);
                isUploading = false;
                file = selectedFile;
            }
        }, 50);
    }

    function clearFile() {
        file = null;
        uploadProgress = 0;
        error = null;
        if (fileInputElement) {
            fileInputElement.value = "";
        }
    }

    function formatFileSize(bytes: number): string {
        if (bytes === 0) return "0 Bytes";
        const k = 1024;
        const sizes = ["Bytes", "KB", "MB", "GB"];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + " " + sizes[i];
    }
</script>

<div class="file-input-container {className}">
    <!-- Drop zone -->
    <div
        class="drop-zone"
        class:dragging={isDragging}
        class:has-file={file !== null}
        on:dragover={handleDragOver}
        on:dragleave={handleDragLeave}
        on:drop={handleDrop}
        on:click={() => fileInputElement?.click()}
        role="button"
        tabindex="0"
    >
        <input
            bind:this={fileInputElement}
            type="file"
            {accept}
            on:change={handleFileSelect}
            style="display: none;"
        />

        {#if file}
            <!-- File selected -->
            <div class="file-info">
                <div class="file-icon">📄</div>
                <div class="file-details">
                    <div class="file-name">{file.name}</div>
                    <div class="file-size">{formatFileSize(file.size)}</div>
                </div>
                <button
                    class="clear-button"
                    on:click|stopPropagation={clearFile}
                    type="button"
                >
                    ✕
                </button>
            </div>
        {:else if isUploading}
            <!-- Upload progress -->
            <div class="upload-progress">
                <div class="progress-text">Uploading... {uploadProgress}%</div>
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: {uploadProgress}%"></div>
                </div>
            </div>
        {:else}
            <!-- Empty state -->
            <div class="empty-state">
                <div class="upload-icon">⬆️</div>
                <div class="placeholder-text">{placeholder}</div>
            </div>
        {/if}
    </div>

    {#if error}
        <div class="error-message">{error}</div>
    {/if}
</div>

<style>
    .file-input-container {
        width: 100%;
    }
    
    .drop-zone {
        padding: 2rem;
        border: 2px dashed var(--edge-soft);
        border-radius: 8px;
        background: var(--surface);
        cursor: pointer;
        transition: all 0.2s ease;
        min-height: 120px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    /* Hover */
    .drop-zone:hover {
        border-color: var(--edge-light);
        background: color-mix(in srgb, var(--surface) 90%, var(--edge-soft));
    }
    
    /* Dragging (accent glow, no “blue-text”) */
    .drop-zone.dragging {
        border-color: var(--accent);
        background: color-mix(in srgb, var(--accent) 20%, var(--surface));
        box-shadow: 0 0 12px color-mix(in srgb, var(--accent) 40%, transparent);
    }
    
    /* Has file */
    .drop-zone.has-file {
        border-style: solid;
        border-color: var(--edge-light);
    }
    
    /* Empty state */
    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.5rem;
        color: var(--text-muted);
        opacity: 0.7;
    }
    
    .upload-icon {
        font-size: 2rem;
    }
    
    .placeholder-text {
        font-size: 0.875rem;
        text-align: center;
    }
    
    /* File info */
    .file-info {
        display: flex;
        align-items: center;
        gap: 1rem;
        width: 100%;
    }
    
    .file-icon {
        font-size: 2rem;
    }
    
    .file-details {
        flex: 1;
        min-width: 0;
    }
    
    .file-name {
        font-weight: 500;
        color: var(--text);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    
    .file-size {
        font-size: 0.75rem;
        color: var(--text-muted);
        opacity: 0.7;
        margin-top: 0.25rem;
    }
    
    /* Clear button (fixed to use your reds) */
    .clear-button {
        padding: 0.5rem;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 1rem;
        line-height: 1;
        transition: all 0.15s ease;
    
        background: var(--red-tint);
        color: var(--red-text);
    }
    
    .clear-button:hover {
        background: var(--red-text);
        color: var(--surface);
    }
    
    /* Upload progress */
    .upload-progress {
        width: 100%;
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }
    
    .progress-text {
        text-align: center;
        font-size: 0.875rem;
        color: var(--text);
    }
    
    /* Progress bar container */
    .progress-bar-container {
        width: 100%;
        height: 8px;
        background: var(--edge-soft);
        border-radius: 4px;
        overflow: hidden;
    }
    
    /* Progress bar itself (accent gradient) */
    .progress-bar {
        height: 100%;
        transition: width 0.3s ease;
        border-radius: 4px;
    
        background: linear-gradient(
            90deg,
            var(--accent),
            var(--accent-secondary, #b57cff)
        );
    }
    
    /* Error message (use your red palette, not external vars) */
    .error-message {
        margin-top: 0.5rem;
        padding: 0.5rem 0.75rem;
        background: color-mix(in srgb, var(--red-text) 20%, transparent);
        color: var(--red-text);
        border-radius: 4px;
        font-size: 0.875rem;
    }
    
</style>
