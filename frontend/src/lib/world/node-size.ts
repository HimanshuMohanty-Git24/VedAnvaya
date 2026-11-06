/** Structural records provide context; subjects and passages carry the visible map. */
export function worldNodeSize(group: number, degree: number) {
    const quiet = group >= 8;
    return quiet ? 0.9 + Math.cbrt(degree) * 0.22 : 2.2 + Math.cbrt(degree) * 0.8;
}
