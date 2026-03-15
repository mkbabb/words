import { test, expect } from '@playwright/test';
import { loadDefinitionOrSkip } from './helpers';

const TEST_WORD = 'hello';
const CONTENT_PATTERN = /greeting|salutation|expression/i;

test.describe('Provider Edit Mode', () => {
  test('edit mode shows editable fields on provider tab', async ({ page }) => {
    const loaded = await loadDefinitionOrSkip(page, TEST_WORD, CONTENT_PATTERN);
    if (!loaded) return;

    // Find and click a provider icon to switch to a provider tab
    // Provider icons are in the WordHeader area — look for non-synthesis source buttons
    const providerIcons = page.locator('[data-provider]');
    const providerCount = await providerIcons.count();

    if (providerCount === 0) {
      test.skip(true, 'No provider tabs available for this word');
      return;
    }

    // Click first provider icon to switch to provider view
    await providerIcons.first().click();
    await page.waitForTimeout(1000);

    // Wait for provider data to load
    const providerContent = page.locator('.border-l-2.border-accent').first();
    await expect(providerContent).toBeVisible({ timeout: 10_000 });

    // Now toggle edit mode via the ThemeSelector edit button
    const editButton = page.locator('button[title*="Edit"], button[title*="edit"]').first();
    if (!(await editButton.isVisible().catch(() => false))) {
      // Try the pencil icon button in ThemeSelector
      const pencilButton = page.locator('button').filter({ has: page.locator('svg.lucide-pencil, svg.lucide-edit') }).first();
      if (await pencilButton.isVisible().catch(() => false)) {
        await pencilButton.click();
      } else {
        test.skip(true, 'Edit button not found — may not be admin');
        return;
      }
    } else {
      await editButton.click();
    }

    await page.waitForTimeout(500);

    // Verify edit mode indicators appear on provider definitions:
    // EditableField in edit mode adds dotted underline styling
    const editableFields = page.locator('.editable-field-wrapper');
    await expect(editableFields.first()).toBeVisible({ timeout: 5_000 });

    // Verify dotted underline decoration is present (edit mode indicator)
    const dottedField = page.locator('[class*="decoration-dotted"]').first();
    await expect(dottedField).toBeVisible({ timeout: 5_000 });
  });

  test('provider definition text is double-click editable', async ({ page }) => {
    const loaded = await loadDefinitionOrSkip(page, TEST_WORD, CONTENT_PATTERN);
    if (!loaded) return;

    // Switch to provider tab
    const providerIcons = page.locator('[data-provider]');
    if ((await providerIcons.count()) === 0) {
      test.skip(true, 'No provider tabs available');
      return;
    }
    await providerIcons.first().click();
    await page.waitForTimeout(1000);

    // Wait for provider content
    await page.locator('.border-l-2.border-accent').first().waitFor({ timeout: 10_000 });

    // Enable edit mode
    const editToggle = page.locator('button').filter({ has: page.locator('svg.lucide-pencil, svg.lucide-edit, svg.lucide-edit-2') }).first();
    if (!(await editToggle.isVisible().catch(() => false))) {
      test.skip(true, 'Edit toggle not visible — may not be admin');
      return;
    }
    await editToggle.click();
    await page.waitForTimeout(500);

    // Find an editable field wrapper and double-click it
    const editableField = page.locator('.editable-field-wrapper').first();
    await expect(editableField).toBeVisible({ timeout: 5_000 });

    // Double-click to activate contenteditable
    await editableField.dblclick();
    await page.waitForTimeout(300);

    // Check that contenteditable is now true on the inner span
    const contentEditable = page.locator('[contenteditable="true"]').first();
    await expect(contentEditable).toBeVisible({ timeout: 3_000 });
  });

  test('synthesized edit mode still works (no regression)', async ({ page }) => {
    const loaded = await loadDefinitionOrSkip(page, 'perspicacious', /keen|perceptive|discern|understand/i);
    if (!loaded) return;

    // Should be on synthesis tab by default for AI-synthesized words
    // Enable edit mode
    const editToggle = page.locator('button').filter({ has: page.locator('svg.lucide-pencil, svg.lucide-edit, svg.lucide-edit-2') }).first();
    if (!(await editToggle.isVisible().catch(() => false))) {
      test.skip(true, 'Edit toggle not visible');
      return;
    }
    await editToggle.click();
    await page.waitForTimeout(500);

    // Verify editable fields appear on synthesized definitions
    const editableFields = page.locator('.editable-field-wrapper');
    await expect(editableFields.first()).toBeVisible({ timeout: 5_000 });

    // Verify dashed outline on the card (edit mode enabled indicator)
    const dashedCard = page.locator('[class*="outline-dashed"]');
    await expect(dashedCard).toBeVisible({ timeout: 3_000 });
  });
});
