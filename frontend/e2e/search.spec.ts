import { test, expect } from '@playwright/test';

const SEARCH_INPUT = 'textarea[aria-label="Search for a word"]';

// The search results dropdown is the second .dropdown-element (SearchControls is first).
// It contains .max-h-64 with result buttons inside.
function getResultsDropdown(page: import('@playwright/test').Page) {
  // Use the results container inside the dropdown — max-h-64 overflow-y-auto
  return page.locator('.max-h-64.overflow-y-auto');
}

function getResultButtons(page: import('@playwright/test').Page) {
  return getResultsDropdown(page).locator('button');
}

test.describe('Search', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('search input is visible and focusable', async ({ page }) => {
    const input = page.locator(SEARCH_INPUT);
    await expect(input).toBeVisible();
    await input.focus();
    await expect(input).toBeFocused();
  });

  test('typing triggers search results', async ({ page }) => {
    const input = page.locator(SEARCH_INPUT);
    // Use type() instead of fill() to trigger input events properly
    await input.click();
    await input.pressSequentially('hello', { delay: 50 });

    // Wait for result buttons to appear
    const results = getResultButtons(page);
    await expect(results.first()).toBeVisible({ timeout: 10_000 });

    const count = await results.count();
    expect(count).toBeGreaterThan(0);
  });

  test('selecting a result navigates to definition', async ({ page }) => {
    const input = page.locator(SEARCH_INPUT);
    await input.click();
    await input.pressSequentially('hello', { delay: 50 });

    const results = getResultButtons(page);
    await expect(results.first()).toBeVisible({ timeout: 10_000 });

    await results.first().click();
    await page.waitForURL(/\/definition\//, { timeout: 15_000 });
  });

  test('keyboard navigation works', async ({ page }) => {
    const input = page.locator(SEARCH_INPUT);
    await input.click();
    await input.pressSequentially('hello', { delay: 50 });

    const results = getResultButtons(page);
    await expect(results.first()).toBeVisible({ timeout: 10_000 });

    // Arrow down + Enter to select
    await input.press('ArrowDown');
    await input.press('Enter');
    await page.waitForURL(/\/definition\//, { timeout: 15_000 });
  });

  test('rapid typing settles to final query', async ({ page }) => {
    const input = page.locator(SEARCH_INPUT);
    await input.click();

    // Type a partial query then clear and type another
    await input.pressSequentially('hel', { delay: 30 });
    await page.waitForTimeout(200);

    // Clear and type different query
    await input.fill('');
    await input.pressSequentially('world', { delay: 50 });

    const results = getResultButtons(page);
    await expect(results.first()).toBeVisible({ timeout: 10_000 });

    // First result should contain "world"
    const text = await results.first().textContent();
    expect(text?.toLowerCase()).toContain('world');
  });
});
