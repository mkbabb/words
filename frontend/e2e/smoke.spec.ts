import { test, expect } from '@playwright/test';

test.describe('Smoke Tests', () => {
  test('homepage loads', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveTitle(/Floridify/);
  });

  test('search input is present on homepage', async ({ page }) => {
    await page.goto('/');
    const input = page.locator('textarea[aria-label="Search for a word"]');
    await expect(input).toBeVisible({ timeout: 10_000 });
  });

  test('search API responds with results', async ({ request }) => {
    // Retry once if the first request fails (backend may be warming up)
    let response = await request.get('/api/v1/search', {
      params: { q: 'test', mode: 'smart', max_results: '5' },
    });
    if (!response.ok()) {
      await new Promise((r) => setTimeout(r, 2000));
      response = await request.get('/api/v1/search', {
        params: { q: 'test', mode: 'smart', max_results: '5' },
      });
    }
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data).toHaveProperty('results');
    expect(data.results.length).toBeGreaterThan(0);
  });

  test('404 page renders for unknown routes', async ({ page }) => {
    await page.goto('/nonexistent-page-xyz');
    await expect(page).toHaveTitle(/Not Found/);
  });

  test('definition deep link loads', async ({ page }) => {
    await page.goto('/definition/hello');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveTitle(/hello/i);
  });
});
