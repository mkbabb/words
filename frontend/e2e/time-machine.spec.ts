import { test, expect } from '@playwright/test';
import { loadDefinitionOrSkip } from './helpers';

// Use a different word than other spec files to reduce rate limit pressure
const TEST_WORD = 'world';
const CONTENT_PATTERN = /earth|planet|globe|people|society|realm|universe|domain/i;

test.describe('TimeMachine', () => {
  test('definition page loads for version history', async ({ page }) => {
    await loadDefinitionOrSkip(page, TEST_WORD, CONTENT_PATTERN);
  });

  test('version history button opens overlay if available', async ({ page }) => {
    const loaded = await loadDefinitionOrSkip(page, TEST_WORD, CONTENT_PATTERN);
    if (!loaded) return;

    // History button uses lucide-history icon
    const historyButton = page.locator('button:has(svg.lucide-history)');
    if (!(await historyButton.isVisible({ timeout: 3_000 }).catch(() => false))) {
      test.skip(true, 'No version history button — word may not have versions');
      return;
    }

    await historyButton.click();

    // TimeMachine overlay
    const heading = page.getByText(/version history/i);
    await expect(heading).toBeVisible({ timeout: 5_000 });
  });

  test('version history API responds', async ({ request }) => {
    const response = await request.get(`/api/v1/words/${TEST_WORD}/versions`);
    expect([200, 404, 429]).toContain(response.status());
  });
});
