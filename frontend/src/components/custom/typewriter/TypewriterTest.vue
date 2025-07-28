<template>
    <div class="p-8 space-y-4">
        <h1 class="text-2xl font-bold mb-4">Typewriter Animation Test</h1>
        
        <div class="space-y-2">
            <label class="block text-sm font-medium">Test Word:</label>
            <input 
                v-model="testWord" 
                type="text" 
                class="px-3 py-2 border rounded-md"
                placeholder="Enter a word"
            />
            <button 
                @click="updateWord"
                class="ml-2 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
            >
                Update Word
            </button>
        </div>
        
        <div class="mt-8 p-4 border rounded-lg">
            <h2 class="text-lg font-semibold mb-2">Animation Output:</h2>
            <div class="text-4xl font-bold">
                <TypewriterText
                    :text="currentWord"
                    mode="human"
                    :base-speed="150"
                    :variance="0.4"
                    :error-rate="0.015"
                    :cursor-blink="true"
                    :start-delay="50"
                />
            </div>
        </div>
        
        <div class="mt-4 text-sm text-gray-600">
            <p>Instructions:</p>
            <ul class="list-disc list-inside">
                <li>First word types quickly (expert mode)</li>
                <li>Subsequent words should show backspace animation before typing</li>
                <li>Watch for visible character-by-character deletion</li>
            </ul>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { TypewriterText } from './index';

const testWord = ref('hello');
const currentWord = ref('hello');

const updateWord = () => {
    currentWord.value = testWord.value;
};
</script>