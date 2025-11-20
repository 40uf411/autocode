export const humanizeResource = (resource) => {
  if (!resource) {
    return 'Administration'
  }

  return resource
    .split(/[_-]/)
    .filter(Boolean)
    .map((chunk) => chunk[0]?.toUpperCase() + chunk.slice(1))
    .join(' ')
}
