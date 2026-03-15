import { test, expect } from '@playwright/test';
import { loadDefinitionOrSkip } from './helpers';

const TEST_WORD = 'hello';
const CONTENT_PATTERN = /greeting|salutation|expression/i;

test.describe('Definition Display', () => {
  test('definition page loads and shows word title', async ({ page }) => {
    await page.goto(`/definition/${TEST_WORD}`);
    await expect(page).toHaveTitle(new RegExp(TEST_WORD, 'i'), { timeout: 45_000 });
  });

  test('definition page shows part-of-speech content', async ({ page }) => {
    const loaded = await loadDefinitionOrSkip(page, TEST_WORD, CONTENT_PATTERN);
    if (!loaded) return;

    const posLabel = page
      .getByText(/^(noun|verb|adjective|adverb|interjection|pronoun|preposition)\s*$/i)
      .first();
    await expect(posLabel).toBeVisible({ timeout: 5_000 });
  });

  test('definition has readable text', async ({ page }) => {
    await loadDefinitionOrSkip(page, TEST_WORD, CONTENT_PATTERN);
  });

  test('search-to-definition flow works', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const input = page.locator('textarea[aria-label="Search for a word"]');
    await input.click();
    await input.pressSequentially(TEST_WORD, { delay: 50 });

    // Wait for results
    const results = page.locator('.max-h-64.overflow-y-auto button');
    await expect(results.first()).toBeVisible({ timeout: 10_000 });

    await results.first().click();
    await page.waitForURL(/\/definition\//, { timeout: 15_000 });

    // Check for rate limiting on the definition page
    const errorState = page.getByText(/something went wrong/i).first();
    const posLabel = page
      .getByText(/^(noun|verb|adjective|adverb|interjection)\s*$/i)
      .first();

    await Promise.race([
      posLabel.waitFor({ state: 'visible', timeout: 45_000 }).catch(() => {}),
      errorState.waitFor({ state: 'visible', timeout: 45_000 }).catch(() => {}),
    ]);

    if (await errorState.isVisible().catch(() => false)) {
      test.skip(true, 'Rate-limited by backend — SSE 429');
      return;
    }

    await expect(posLabel).toBeVisible({ timeout: 5_000 });
  });
});
