// @ts-check
const { test, expect } = require("@playwright/test");

test.describe("Jarvis view", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    // Jarvis is the default view
    await expect(page.locator(".app-nav-btn.is-active")).toHaveText("Jarvis");
  });

  test("page loads with header and nav buttons", async ({ page }) => {
    await expect(page.locator(".app-brand")).toBeVisible();
    const navBtns = page.locator(".app-nav-btn");
    await expect(navBtns.first()).toBeVisible();
    expect(await navBtns.count()).toBeGreaterThan(3);
  });

  test("Jarvis view renders control panel inputs", async ({ page }) => {
    // Control panel should have inputs with data-key attributes
    const cpInputs = page.locator("input[data-key]");
    await expect(cpInputs.first()).toBeVisible();
    expect(await cpInputs.count()).toBeGreaterThan(3);
  });

  test("Document / CIF table renders with rows", async ({ page }) => {
    const docCifInputs = page.locator('input[data-doc-cif-field="country"]');
    await expect(docCifInputs.first()).toBeVisible({ timeout: 10_000 });
    expect(await docCifInputs.count()).toBeGreaterThan(0);
  });

  test("Controlling columns (USD/Bale and Pts/lb) are present", async ({ page }) => {
    const usdBaleInputs = page.locator('input[data-doc-cif-field="USDA_USD_BALE"]');
    await expect(usdBaleInputs.first()).toBeVisible({ timeout: 10_000 });

    const ptsLbInputs = page.locator('input[data-doc-cif-field="USDA_PTS_LB"]');
    await expect(ptsLbInputs.first()).toBeVisible();
    // Pts/lb should be readonly
    await expect(ptsLbInputs.first()).toHaveAttribute("readonly", "");
  });

  test("Pts/lb updates live when USD/Bale changes", async ({ page }) => {
    const usdInput = page.locator('input[data-doc-cif-field="USDA_USD_BALE"]').first();
    const ptsInput = page.locator('input[data-doc-cif-field="USDA_PTS_LB"]').first();
    await expect(usdInput).toBeVisible({ timeout: 10_000 });

    await usdInput.fill("0.617");
    // ceil5(((0.617 * 90) / 20) / 22.046 * 100) = ceil5(12.59) = 15
    await expect(ptsInput).toHaveValue("15");
  });

  test("Show notes checkbox toggles floating modal on click", async ({ page }) => {
    const notesCb = page.locator("#jarvis-show-notes");
    await expect(notesCb).toBeVisible();
    await notesCb.check();

    // Click a control panel input
    const cpInput = page.locator("input[data-key]").first();
    await cpInput.click();

    // Modal should appear
    const modal = page.locator("#jarvis-notes-modal");
    await expect(modal).toBeVisible({ timeout: 2_000 });
    const text = await modal.textContent();
    expect(text).toContain("control_panel");
  });
});

test.describe("Navigation", () => {
  test("switching views works", async ({ page }) => {
    await page.goto("/");

    // Click USD nav button
    const usdBtn = page.locator('.app-nav-btn:text("USD")');
    await usdBtn.click();
    await expect(usdBtn).toHaveClass(/is-active/);
    // USD table should appear
    await expect(page.locator("#usd-table-host")).toBeVisible({ timeout: 15_000 });

    // Click PTS nav button
    const ptsBtn = page.locator('.app-nav-btn:text("PTS")');
    await ptsBtn.click();
    await expect(ptsBtn).toHaveClass(/is-active/);
    await expect(page.locator("#pts-table-host")).toBeVisible({ timeout: 15_000 });

    // Click CIF nav button
    const cifBtn = page.locator('.app-nav-btn:text("CIF")');
    await cifBtn.click();
    await expect(cifBtn).toHaveClass(/is-active/);
  });

  test("Documentation view renders mermaid diagrams", async ({ page }) => {
    await page.goto("/");
    const docBtn = page.locator('.app-nav-btn:text("Documentation")');
    await docBtn.click();
    await expect(docBtn).toHaveClass(/is-active/);

    // Should show diagram cards
    const cards = page.locator(".doc-diagram-card");
    await expect(cards.first()).toBeVisible({ timeout: 10_000 });
    expect(await cards.count()).toBeGreaterThanOrEqual(6);
  });

  test("LC_Bank_Cost view renders table", async ({ page }) => {
    await page.goto("/");
    const lcBtn = page.locator('.app-nav-btn:text("LC_Bank_Cost")');
    await lcBtn.click();
    await expect(lcBtn).toHaveClass(/is-active/);

    // Should show bank cost inputs
    const bankInputs = page.locator("input[data-bank]");
    await expect(bankInputs.first()).toBeVisible({ timeout: 10_000 });
    expect(await bankInputs.count()).toBeGreaterThan(10);
  });
});

test.describe("Save toast", () => {
  test("save control panel shows toast", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("input[data-key]").first()).toBeVisible({ timeout: 10_000 });

    // Find and click the first Save button in the Jarvis view
    const saveBtn = page.locator('button:text("Save")').first();
    await saveBtn.click();

    // Toast should appear
    const toast = page.locator("#save-toast");
    await expect(toast).toBeVisible({ timeout: 3_000 });
    const text = await toast.textContent();
    expect(text.toLowerCase()).toContain("saved");
  });
});
