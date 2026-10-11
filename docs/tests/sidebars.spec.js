import { expect, test } from "@playwright/test";

const reference = "/reference/mobjects/";
const desktop = ".md-sidebar--primary .md-sidebar__scrollwrap";

async function bottom(page, javaScriptEnabled = true) {
  await page.evaluate(() => scrollTo(0, document.documentElement.scrollHeight));
  if (javaScriptEnabled) {
    await page.evaluate(
      () =>
        new Promise((done) =>
          requestAnimationFrame(() => requestAnimationFrame(done)),
        ),
    );
  }
}

// Check rendered geometry, not CSS declarations. A zero-height parent with an
// overflowing child is exactly the failure these assertions must detect.
async function contained(page) {
  await expect
    .poll(() =>
      page.evaluate(() => {
        const main = document.querySelector(".md-main").getBoundingClientRect();
        return [...document.querySelectorAll(".md-sidebar")].flatMap(
          (sidebar) => {
            if (
              getComputedStyle(sidebar).position !== "sticky" ||
              sidebar.hidden
            )
              return [];
            const wrap = sidebar.querySelector(".md-sidebar__scrollwrap");
            const box = wrap.getBoundingClientRect();
            const parent = sidebar.getBoundingClientRect();
            const failures = [];
            if (box.bottom > main.bottom + 1) failures.push("crosses footer");
            if (box.bottom > parent.bottom + 1) failures.push("escapes parent");
            if (box.height > innerHeight + 1) failures.push("exceeds viewport");
            return failures.map(
              (failure) => `${sidebar.dataset.mdType}: ${failure}`,
            );
          },
        );
      }),
    )
    .toEqual([]);
}

async function failPreview(page, failure) {
  // Fail a real preview request. Check the network outcome, so this regression
  // stays valid if a future theme release learns to contain preview errors.
  await page.route("**/reference/mobjects/style/", (route) =>
    failure === "network"
      ? route.abort("failed")
      : route.fulfill({ status: 503, body: "Unavailable" }),
  );
  const failed = page.waitForEvent(
    failure === "network" ? "requestfailed" : "requestfinished",
    (request) =>
      new URL(request.url()).pathname === "/reference/mobjects/style/",
  );
  await page
    .getByRole("link", { name: "the style keywords", exact: true })
    .hover();
  const request = await failed;
  if (failure === "http") expect((await request.response()).status()).toBe(503);
  await page.mouse.move(800, 30);
}

for (const state of ["healthy", "network", "http", "bundle unavailable"]) {
  test(`sidebars stay contained: ${state}`, async ({ page }) => {
    if (state === "bundle unavailable") {
      await page.route("**/assets/javascripts/bundle.*.min.js", (route) =>
        route.abort(),
      );
    }
    await page.goto(reference);
    if (state === "network" || state === "http") await failPreview(page, state);

    // Both responsive boundaries, changing root font sizes, and a footer taller
    // than the viewport. Resize repeatedly in the same document, without reloads.
    for (const [width, height] of [
      [1568, 1088],
      [1568, 500],
      [1568, 300],
      [1800, 800],
      [1280, 600],
      [1220, 768],
      [1219, 768],
      [960, 768],
      [1568, 1088],
    ]) {
      await page.setViewportSize({ width, height });
      await page.evaluate(() => scrollTo(0, 0));
      await contained(page);
      await bottom(page);
      await contained(page);
    }

    // Every link remains reachable by scrolling the sidebar independently.
    await page.evaluate(() => scrollTo(0, 200));
    const wrap = page.locator(desktop);
    const last = wrap.locator("a:visible").last();
    await expect
      .poll(() =>
        last.evaluate((link) => {
          const wrap = link.closest(".md-sidebar__scrollwrap");
          // Resize and scroll events can still change the layout. Scroll and
          // measure together, using the sidebar's current geometry.
          wrap.scrollTop = wrap.scrollHeight;
          const box = wrap.getBoundingClientRect();
          const target = link.getBoundingClientRect();
          return target.top >= box.top - 1 && target.bottom <= box.bottom + 1;
        }),
      )
      .toBe(true);
    expect(await page.evaluate(() => scrollY)).toBe(200);
  });
}

for (const failed of [false, true]) {
  test(`instant navigation and history${failed ? " after a preview failure" : ""}`, async ({
    page,
  }) => {
    await page.goto(reference);
    const documentId = await page.evaluate(() => {
      window.sidebarTestId = Math.random();
      return window.sidebarTestId;
    });
    if (failed) await failPreview(page, "network");
    await page.locator('a[href$="changelog/"]').first().click();
    await expect(page).toHaveURL(/\/changelog\/$/);
    await expect(page.locator(".md-content h1")).toContainText("Changelog");
    await page.setViewportSize({ width: 1568, height: 300 });
    await bottom(page);
    await contained(page);
    await page.goBack();
    await expect(page.locator(".md-content h1")).toContainText("Mobjects");
    await bottom(page);
    await contained(page);
    expect(await page.evaluate(() => window.sidebarTestId)).toBe(documentId);
  });
}

test("healthy previews still open", async ({ page }) => {
  await page.goto(reference);
  await page
    .getByRole("link", { name: "the style keywords", exact: true })
    .hover();
  await expect(page.locator(".md-tooltip2")).toBeVisible();
  await contained(page);
});

test("mobile drawer and floating table of contents still scroll", async ({
  page,
}) => {
  for (const [width, height] of [
    [390, 844],
    [844, 390],
    [959, 768],
  ]) {
    await page.setViewportSize({ width, height });
    await page.goto(reference);
    await page.locator('.md-header label[for="__drawer"]').click();
    await expect(page.locator("#__drawer")).toBeChecked();
    const wrap = page.locator(desktop);
    await expect
      .poll(() =>
        wrap.evaluate((el) => {
          const box = el.getBoundingClientRect();
          return box.left >= 0 && box.top >= 0 && box.bottom <= innerHeight;
        }),
      )
      .toBe(true);
    await wrap.evaluate((el) => {
      el.scrollTop = el.scrollHeight;
    });
    await expect
      .poll(() => wrap.evaluate((el) => el.scrollTop))
      .toBeGreaterThan(0);
    const overlay = page.locator('label.md-overlay[for="__drawer"]');
    const position = await overlay.evaluate((el) => {
      const box = el.getBoundingClientRect();
      const drawer = document
        .querySelector(".md-sidebar--primary")
        .getBoundingClientRect();
      // The viewport edge can be a scrollbar gutter, outside the overlay.
      return {
        x: (drawer.right + box.right) / 2 - box.left,
        y: box.height / 2,
      };
    });
    await overlay.click({ position });
    await expect(page.locator("#__drawer")).not.toBeChecked();
    await page.locator('.md-sidebar-button[for="__toc"]').click();
    await expect(page.locator("#__toc")).toBeChecked();
    await expect(
      page.locator(".md-sidebar--secondary .md-sidebar__inner"),
    ).toHaveCSS("opacity", "1");
  }
});

test.describe("without JavaScript", () => {
  test.use({ javaScriptEnabled: false });
  test("deep links and short pages remain contained", async ({ page }) => {
    for (const url of [reference + "#manimgx.Mobject.name", "/changelog/"]) {
      await page.goto(url);
      await bottom(page, false);
      await contained(page);
    }
  });
});

test("print hides both sidebars", async ({ page }) => {
  await page.goto(reference);
  await page.emulateMedia({ media: "print" });
  await expect(page.locator(".md-sidebar--primary")).toBeHidden();
  await expect(page.locator(".md-sidebar--secondary")).toBeHidden();
});
