import { ref, watch, onUnmounted, type Ref } from 'vue';
import { audioApi, type GenerateAudioResponse } from '@/api/audio';
import type { AudioFile } from '@/types/api';

export type AudioPlaybackState = 'idle' | 'loading' | 'playing' | 'error';

export function useAudioPlayback(
  word: Ref<string>,
  audioFiles: Ref<AudioFile[] | undefined>,
) {
  const state = ref<AudioPlaybackState>('idle');
  const errorMessage = ref('');
  let audioElement: HTMLAudioElement | null = null;
  let cachedUrl: string | null = null;

  function cleanup() {
    if (audioElement) {
      audioElement.pause();
      audioElement.removeAttribute('src');
      audioElement.load();
      audioElement = null;
    }
    cachedUrl = null;
  }

  async function resolveAudioUrl(): Promise<string> {
    // If we already have a cached URL for this word, reuse it
    if (cachedUrl) return cachedUrl;

    // Check existing audio files from the word data
    const files = audioFiles.value;
    if (files && files.length > 0) {
      const file = files[0];
      if (file.url) {
        cachedUrl = audioApi.getAudioContentUrl(file.url);
        return cachedUrl;
      }
    }

    // Generate on demand
    const result: GenerateAudioResponse = await audioApi.generateAudio({
      word: word.value,
    });
    cachedUrl = audioApi.getAudioContentUrl(result.content_url);
    return cachedUrl;
  }

  async function play() {
    if (state.value === 'loading') return;

    // If already playing, stop
    if (state.value === 'playing' && audioElement) {
      audioElement.pause();
      audioElement.currentTime = 0;
      state.value = 'idle';
      return;
    }

    state.value = 'loading';
    errorMessage.value = '';

    try {
      const url = await resolveAudioUrl();

      if (!audioElement) {
        audioElement = new Audio();
      }

      audioElement.src = url;

      audioElement.onended = () => {
        state.value = 'idle';
      };

      audioElement.onerror = () => {
        state.value = 'error';
        errorMessage.value = 'Failed to play audio';
      };

      await audioElement.play();
      state.value = 'playing';
    } catch (e) {
      state.value = 'error';
      errorMessage.value = e instanceof Error ? e.message : 'Audio playback failed';
    }
  }

  // Reset when word changes
  watch(word, () => {
    if (state.value === 'playing' && audioElement) {
      audioElement.pause();
    }
    state.value = 'idle';
    cachedUrl = null;
  });

  onUnmounted(() => {
    cleanup();
  });

  return {
    state,
    errorMessage,
    play,
  };
}
