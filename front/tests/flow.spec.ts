import { test, expect } from '@playwright/test';

// A tiny 1x1 grayscale+alpha PNG fails createImageBitmap decoding in Chrome; use a plain 4x4 RGB PNG instead.
const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAQAAAAECAIAAAAmkwkpAAAAEUlEQVR4nGP8z4AATEhsPBwAM9EBBzDn4UwAAAAASUVORK5CYII=', 'base64');

test('upload, crop, automatic progress, chat, edit, delete', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto('/');
  await page.locator('input[type=file]').last().setInputFiles({ name: 'menu.png', mimeType: 'image/png', buffer: png });
  await expect(page.getByText('분석할 영역 선택')).toBeVisible();
  await page.getByRole('button', { name: '사진 회전' }).click();
  await page.getByRole('button', { name: '분석 시작하기' }).click();
  await expect(page.getByText('분석이 완료됐어요')).toBeVisible();
  await expect(page.getByText('모의 모드 —', { exact: false })).toBeVisible();
  await expect(page.locator('article')).toHaveCount(2);
  await page.getByRole('textbox', { name: '후속 질문 입력' }).fill('그 음식은 어떻게 조리해?');
  await page.getByRole('button', { name: '질문 보내기' }).click();
  await expect(page.getByText('어떤 음식을 말씀하시는지', { exact: false })).toBeVisible();
  await page.getByRole('button', { name: '원문 수정', exact: true }).first().click();
  await page.getByRole('textbox', { name: '수정할 원문 입력' }).fill('醤油ラーメン');
  await page.getByRole('button', { name: '수정 후 재분석' }).click();
  await expect(page.getByText('분석이 완료됐어요')).toBeVisible();
  await expect(page.getByText('醤油ラーメン', { exact: true }).first()).toBeVisible();
  await page.getByRole('button', { name: '출처 보기' }).first().click();
  await expect(page.getByRole('dialog', { name: '출처 보기' })).toBeVisible();
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: '분석 삭제', exact: true }).click();
  await page.getByRole('button', { name: '삭제', exact: true }).click();
  await expect(page).toHaveURL('/');
  expect(errors).toEqual([]);
  expect(await page.evaluate(() => sessionStorage.getItem('menu-decoder-session'))).toBeNull();
});

test('an unrelated tab cannot access an analysis', async ({ page }) => {
  await page.goto('/analyses/00000000-0000-0000-0000-000000000000');
  await expect(page.getByText('이용 중인 세션이 만료됐거나', { exact: false })).toBeVisible();
  await expect(page.locator('article')).toHaveCount(0);
});
