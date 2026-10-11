import { expect, test } from "@playwright/test";

for (const colorScheme of ["light", "dark"]) {
  test.describe(`system prefers ${colorScheme}`, () => {
    test.use({ colorScheme });

    test("starts with the system preference, then remembers a two-way toggle", async ({
      page,
    }) => {
      const initial = colorScheme === "dark" ? "slate" : "default";
      const opposite = colorScheme === "dark" ? "default" : "slate";
      const palette = page.locator('[data-md-component="palette"]');
      const toggle = palette.locator("label:visible");
      const body = page.locator("body");

      await page.goto("/changelog/");
      await expect(palette.locator("input")).toHaveCount(2);
      await expect(body).toHaveAttribute("data-md-color-scheme", initial);
      await toggle.click();
      await expect(body).toHaveAttribute("data-md-color-scheme", opposite);
      await toggle.click();
      await expect(body).toHaveAttribute("data-md-color-scheme", initial);

      // A manual choice survives an OS change, instant navigation, and reload.
      await page.emulateMedia({
        colorScheme: colorScheme === "dark" ? "light" : "dark",
      });
      await expect(body).toHaveAttribute("data-md-color-scheme", initial);
      await page.locator('a[href$="developer-guide/"]').first().click();
      await expect(page).toHaveURL(/\/developer-guide\/$/);
      await expect(body).toHaveAttribute("data-md-color-scheme", initial);
      await page.reload();
      await expect(body).toHaveAttribute("data-md-color-scheme", initial);
      await toggle.click();
      await expect(body).toHaveAttribute("data-md-color-scheme", opposite);
    });
  });
}
