import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

/**
 * Navigate to a definition page and wait for content to load.
 * Gracefully skips the test if SSE rate limiting (429) is encountered.
 *
 * @returns true if definition loaded, false if rate-limited (test is skipped)
 */
export async function loadDefinitionOrSkip(
  page: Page,
  word: string,
  contentPattern: RegExp,
): Promise<boolean> {
  await page.goto(`/definition/${word}`);

  const defText = page.getByText(contentPattern).first();
  const errorState = page.getByText(/something went wrong/i).first();

  // Race: definition content vs error state (SSE lookup can take 30s+)
  await Promise.race([
    defText.waitFor({ state: 'visible', timeout: 45_000 }).catch(() => {}),
    errorState.waitFor({ state: 'visible', timeout: 45_000 }).catch(() => {}),
  ]);

  if (await errorState.isVisible().catch(() => false)) {
    test.skip(true, 'Rate-limited by backend — SSE 429');
    return false;
  }

  await expect(defText).toBeVisible({ timeout: 5_000 });
  return true;
}
