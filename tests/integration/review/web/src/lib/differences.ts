import type { Attachment } from 'svelte/attachments'

async function load(url: string): Promise<HTMLImageElement> {
  const image = new Image()
  image.src = url
  await image.decode()
  return image
}

function pixels(image: HTMLImageElement): Uint8ClampedArray {
  const { naturalWidth: width, naturalHeight: height } = image
  const context = new OffscreenCanvas(width, height).getContext('2d')!
  context.drawImage(image, 0, 0)
  return context.getImageData(0, 0, width, height).data
}

/** Draws where two frames differ: each pixel's largest channel difference, as heat (black,
 * then red, yellow, white as the difference grows; square-rooted, so faint differences show). */
export function differences(
  a: string,
  b: string,
  onError: (message: string) => void,
): Attachment<HTMLCanvasElement> {
  return (canvas) => {
    let live = true
    Promise.all([load(a), load(b)])
      .then(([first, second]) => {
        if (!live) return
        const width = first.naturalWidth
        const height = first.naturalHeight
        const one = pixels(first)
        const two = pixels(second)
        canvas.width = width
        canvas.height = height
        const context = canvas.getContext('2d')!
        const heat = context.createImageData(width, height)
        for (let p = 0; p < one.length; p += 4) {
          const d = Math.max(
            Math.abs(one[p]! - two[p]!),
            Math.abs(one[p + 1]! - two[p + 1]!),
            Math.abs(one[p + 2]! - two[p + 2]!),
          )
          const v = Math.sqrt(d / 255) * 765
          heat.data[p] = v
          heat.data[p + 1] = v - 255
          heat.data[p + 2] = v - 510
          heat.data[p + 3] = 255
        }
        context.putImageData(heat, 0, 0)
      })
      .catch((error: unknown) => {
        if (live) onError(error instanceof Error ? error.message : String(error))
      })
    return () => {
      live = false
    }
  }
}
