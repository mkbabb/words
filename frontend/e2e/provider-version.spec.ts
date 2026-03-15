import { test, expect } from '@playwright/test';

const TEST_WORD = 'hello';

test.describe('Provider & Version APIs', () => {
  test('semantic status API returns ready state', async ({ request }) => {
    const response = await request.get('/api/v1/search/semantic/status');
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data).toHaveProperty('ready');
  });

  test('provider list API responds', async ({ request }) => {
    const response = await request.get(`/api/v1/lookup/${TEST_WORD}/providers`);
    expect([200, 404, 429]).toContain(response.status());
  });

  test('version history API responds', async ({ request }) => {
    const response = await request.get(`/api/v1/words/${TEST_WORD}/versions`);
    expect([200, 404, 429]).toContain(response.status());
  });

  test('search API returns results with metadata', async ({ request }) => {
    const response = await request.get('/api/v1/search', {
      params: { q: 'test', mode: 'smart', max_results: '5' },
    });
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.results.length).toBeGreaterThan(0);
    expect(data.results[0]).toHaveProperty('word');
    expect(data.results[0]).toHaveProperty('method');
    expect(data.results[0]).toHaveProperty('score');
  });
});
