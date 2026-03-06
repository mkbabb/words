import { ref, watch, onUnmounted, type Ref } from 'vue';
import { audioApi, type GenerateAudioResponse } from '@/api/audio';
import type { AudioFile } from '@/types/api';

export type AudioPlaybackState = 'idle' | 'loading' | 'playing' | 'error';

export function useAudioPlayback(
  word: Ref<string>,
  audioFiles: Ref<AudioFile[] | undefined>,
  language: Ref<string> = ref('en'),
) {
  const state = ref<AudioPlaybackState>('idle');
  const errorMessage = ref('');
  let audioElement: HTMLAudioElement | null = null;
  let cachedUrl: string | null = null;
  let triedExistingFiles = false;

  function cleanup() {
    if (audioElement) {
      audioElement.pause();
      audioElement.removeAttribute('src');
      audioElement.load();
      audioElement = null;
    }
    cachedUrl = null;
  }

  function matchesRequestedLanguage(file: AudioFile, requestedLanguage: string): boolean {
    if (requestedLanguage === 'en') {
      return !file.accent || file.accent === 'en' || file.accent === 'american' || file.accent === 'british';
    }
    return file.accent === requestedLanguage;
  }

  async function resolveAudioUrl(): Promise<string> {
    // If we already have a cached URL for this word, reuse it
    if (cachedUrl) return cachedUrl;

    // Check existing audio files from the word data (skip if a previous attempt failed)
    if (!triedExistingFiles) {
      const files = audioFiles.value;
      if (files && files.length > 0) {
        const file = files.find((candidate) =>
          matchesRequestedLanguage(candidate, language.value)
        );
        if (file?.url) {
          triedExistingFiles = true;
          cachedUrl = audioApi.getAudioContentUrl(file.url);
          return cachedUrl;
        }
      }
    }

    // Generate via backend TTS (language-aware)
    const result: GenerateAudioResponse = await audioApi.generateAudio({
      word: word.value,
      language: language.value,
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
        cachedUrl = null;
      };

      await audioElement.play();
      state.value = 'playing';
    } catch (e) {
      state.value = 'error';
      cachedUrl = null;
      errorMessage.value =
        e instanceof Error ? e.message : 'No pronunciation audio available';
    }
  }

  // Reset when word changes
  watch(word, () => {
    if (state.value === 'playing' && audioElement) {
      audioElement.pause();
    }
    state.value = 'idle';
    cachedUrl = null;
    triedExistingFiles = false;
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
