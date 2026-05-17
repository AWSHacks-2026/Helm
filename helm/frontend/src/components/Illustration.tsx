const sources = {
  "hero-course-lines": new URL(
    "../assets/illustrations/hero-course-lines.svg",
    import.meta.url,
  ).href,
  "empty-ledger": new URL("../assets/illustrations/empty-ledger.svg", import.meta.url)
    .href,
} as const;

export type IllustrationName = keyof typeof sources;

type Props = {
  name: IllustrationName;
  alt: string;
  className?: string;
};

export function Illustration({ name, alt, className }: Props) {
  const src = sources[name];
  return (
    <img
      src={src}
      alt={alt}
      className={className}
      role="img"
      loading="lazy"
      decoding="async"
    />
  );
}
