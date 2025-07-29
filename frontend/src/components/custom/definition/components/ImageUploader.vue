<template>
    <div class="relative">
        <!-- Upload Button/Icon -->
        <button
            v-if="variant === 'empty'"
            class="flex flex-col items-center justify-center w-full h-full text-muted-foreground hover:text-foreground transition-all duration-300 hover:scale-105"
            @click="triggerFileInput"
            :disabled="isUploading"
        >
            <Transition name="upload-icon" mode="out-in">
                <LoaderIcon v-if="isUploading" class="w-8 h-8 mb-2 animate-spin" />
                <CameraIcon v-else class="w-8 h-8 mb-2" />
            </Transition>
            <span class="text-sm font-medium">{{ isUploading ? 'Uploading...' : 'Add Image' }}</span>
            <span v-if="isUploading" class="text-xs text-muted-foreground mt-1 animate-pulse">Please wait...</span>
        </button>

        <button
            v-else
            :class="buttonClasses"
            @click="triggerFileInput"
            :disabled="isUploading"
            :title="isUploading ? 'Uploading...' : 'Add image'"
        >
            <Transition name="upload-icon" mode="out-in">
                <LoaderIcon v-if="isUploading" class="animate-spin" :class="iconClasses" />
                <CameraIcon v-else :class="iconClasses" />
            </Transition>
        </button>

        <!-- File Input (Hidden) -->
        <input
            ref="fileInput"
            type="file"
            accept="image/*"
            multiple
            class="hidden"
            @change="handleFileSelect"
        />

        <!-- Upload Progress (if needed) -->
        <Transition name="progress-fade">
            <div 
                v-if="isUploading && showProgress"
                class="absolute inset-x-0 bottom-0 bg-black/50 text-white text-xs text-center py-1 rounded-b-lg backdrop-blur-sm"
            >
                {{ uploadProgress }}%
            </div>
        </Transition>
    </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { CameraIcon, LoaderIcon } from 'lucide-vue-next';
import { useToast } from '@/components/ui/toast/use-toast';
import type { ImageMedia } from '@/types/api';

interface ImageUploaderProps {
    synthEntryId?: string;
    size?: 'sm' | 'lg';
    variant?: 'icon' | 'empty';
    showProgress?: boolean;
}

const props = withDefaults(defineProps<ImageUploaderProps>(), {
    size: 'sm',
    variant: 'icon',
    showProgress: false,
});

const emit = defineEmits<{
    'upload-start': [];
    'upload-progress': [progress: number];
    'upload-success': [images: ImageMedia[]];
    'upload-error': [error: string];
}>();

// State
const fileInput = ref<HTMLInputElement>();
const isUploading = ref(false);
const uploadProgress = ref(0);
const { toast } = useToast();

// Computed classes
const buttonClasses = computed(() => {
    const base = "flex items-center justify-center rounded-full transition-all duration-200 hover:scale-110";
    const sizes = {
        sm: "w-6 h-6 bg-black/50 hover:bg-black/70",
        lg: "w-12 h-12 bg-primary/80 hover:bg-primary"
    };
    return `${base} ${sizes[props.size]}`;
});

const iconClasses = computed(() => {
    const sizes = {
        sm: "w-3 h-3",
        lg: "w-6 h-6"
    };
    return `${sizes[props.size]} text-white`;
});

// Methods
const triggerFileInput = () => {
    if (fileInput.value && !isUploading.value) {
        fileInput.value.click();
    }
};

const handleFileSelect = async (event: Event) => {
    const input = event.target as HTMLInputElement;
    const files = input.files;
    
    if (!files || files.length === 0) return;
    if (!props.synthEntryId) {
        toast({
            title: "Error",
            description: "No entry ID provided for image upload",
            variant: "destructive",
        });
        return;
    }

    // Validate files
    const validFiles = Array.from(files).filter(file => {
        if (!file.type.startsWith('image/')) {
            toast({
                title: "Invalid File",
                description: `${file.name} is not an image file`,
                variant: "destructive",
            });
            return false;
        }
        
        if (file.size > 10 * 1024 * 1024) { // 10MB limit
            toast({
                title: "File Too Large",
                description: `${file.name} is larger than 10MB`,
                variant: "destructive",
            });
            return false;
        }
        
        return true;
    });

    if (validFiles.length === 0) return;

    try {
        isUploading.value = true;
        uploadProgress.value = 0;
        emit('upload-start');

        const uploadedImages: ImageMedia[] = [];

        // Upload files sequentially to avoid overwhelming the server
        for (let i = 0; i < validFiles.length; i++) {
            const file = validFiles[i];
            
            try {
                const result = await uploadSingleFile(file);
                uploadedImages.push(result);
                
                // Update progress
                uploadProgress.value = Math.round(((i + 1) / validFiles.length) * 100);
                emit('upload-progress', uploadProgress.value);
                
            } catch (error) {
                console.error(`Failed to upload ${file.name}:`, error);
                toast({
                    title: "Upload Failed",
                    description: `Failed to upload ${file.name}`,
                    variant: "destructive",
                });
            }
        }

        if (uploadedImages.length > 0) {
            emit('upload-success', uploadedImages);
            toast({
                title: "Upload Successful",
                description: `Successfully uploaded ${uploadedImages.length} image${uploadedImages.length > 1 ? 's' : ''}`,
                variant: "default",
            });
        }

    } catch (error) {
        console.error('Upload error:', error);
        emit('upload-error', error instanceof Error ? error.message : 'Upload failed');
        toast({
            title: "Upload Error",
            description: "An unexpected error occurred during upload",
            variant: "destructive",
        });
    } finally {
        isUploading.value = false;
        uploadProgress.value = 0;
        
        // Clear the input so the same file can be selected again
        if (input) {
            input.value = '';
        }
    }
};

const uploadSingleFile = async (file: File): Promise<ImageMedia> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('alt_text', file.name.replace(/\.[^/.]+$/, "")); // Remove extension for alt text

    // Use fetch with progress tracking if possible
    const response = await fetch(`/api/v1/synth-entries/${props.synthEntryId}/images/upload`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Upload failed: ${response.status} ${errorText}`);
    }

    const result = await response.json();
    
    // The backend should return the updated entry with new images
    // For now, we'll construct the ImageMedia object from the response
    return {
        id: result.data.image_id || result.image_id,
        url: `/api/v1/images/${result.data.image_id || result.image_id}/content`,
        format: file.type.split('/')[1] || 'unknown',
        size_bytes: file.size,
        width: 0, // Will need to be determined by backend
        height: 0, // Will need to be determined by backend
        alt_text: formData.get('alt_text') as string || 'Uploaded image',
        description: undefined,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        version: 1,
    };
};
</script>

<style scoped>
/* Icon transition animations */
.upload-icon-enter-active {
    transition: all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.upload-icon-leave-active {
    transition: all 0.15s cubic-bezier(0.55, 0.055, 0.675, 0.19);
}

.upload-icon-enter-from {
    opacity: 0;
    transform: scale(0.9) rotate(90deg);
}

.upload-icon-enter-to {
    opacity: 1;
    transform: scale(1) rotate(0deg);
}

.upload-icon-leave-from {
    opacity: 1;
    transform: scale(1) rotate(0deg);
}

.upload-icon-leave-to {
    opacity: 0;
    transform: scale(1.1) rotate(-90deg);
}

/* Progress fade animations */
.progress-fade-enter-active {
    transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.progress-fade-leave-active {
    transition: all 0.2s cubic-bezier(0.55, 0.055, 0.675, 0.19);
}

.progress-fade-enter-from {
    opacity: 0;
    transform: translateY(0.5rem);
}

.progress-fade-enter-to {
    opacity: 1;
    transform: translateY(0);
}

.progress-fade-leave-from {
    opacity: 1;
    transform: translateY(0);
}

.progress-fade-leave-to {
    opacity: 0;
    transform: translateY(-0.25rem);
}
</style>