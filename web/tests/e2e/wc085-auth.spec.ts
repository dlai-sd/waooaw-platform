import { expect, test } from '@playwright/test';

test('WC085 SP-01/SP-08: switching auth dismisses directly to the public origin', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto('/professionals');
  const trigger = page.getByRole('link', { name: 'Log in', exact: true });
  await trigger.click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByRole('heading', { name: 'Welcome back' })).toBeVisible();
  expect(await dialog.evaluate((element) => element.scrollHeight <= element.clientHeight + 1)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath('login-1366.png'), fullPage: true });
  const initial = await dialog.boundingBox();
  await dialog.getByRole('link', { name: 'Create an account' }).click();
  await expect(dialog.getByRole('heading', { name: 'Create your WAOOAW account' })).toBeVisible();
  expect(await dialog.evaluate((element) => element.scrollHeight <= element.clientHeight + 1)).toBe(true);
  const switched = await dialog.boundingBox();
  expect(Math.abs((initial?.width ?? 0) - (switched?.width ?? 0))).toBeLessThanOrEqual(1);
  expect(Math.abs((initial?.height ?? 0) - (switched?.height ?? 0))).toBeLessThanOrEqual(1);
  await page.screenshot({ path: testInfo.outputPath('register-1366.png'), fullPage: true });
  await page.keyboard.press('Escape');
  await expect(page).toHaveURL(/\/professionals$/);
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(trigger).toBeFocused();
});

test('WC085 SP-08: dismissed modal stays closed on public navigation', async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto('/');
  await page.getByRole('link', { name: 'Log in', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('button', { name: 'Close', exact: true }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.goto('/login');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible();
});