/** Renders inline media for YouTube, Giphy, and direct image URLs found in text. */

const YOUTUBE_RE = /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([A-Za-z0-9_-]{11})/;
const GIPHY_RE = /https?:\/\/(?:media\.giphy\.com\/media|giphy\.com\/gifs)\/([A-Za-z0-9-]+)/;
const IMAGE_RE = /https?:\/\/\S+\.(?:png|jpg|jpeg|gif|webp)(?:\?\S*)?/i;

interface Props {
  url: string;
}

export function MediaEmbed({ url }: Props) {
  const ytMatch = url.match(YOUTUBE_RE);
  if (ytMatch) {
    return (
      <div className="forum-embed forum-embed--video">
        <iframe
          src={`https://www.youtube-nocookie.com/embed/${ytMatch[1]}`}
          title="YouTube video"
          allowFullScreen
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        />
      </div>
    );
  }

  const giphyMatch = url.match(GIPHY_RE);
  if (giphyMatch) {
    return (
      <div className="forum-embed forum-embed--gif">
        <img
          src={`https://media.giphy.com/media/${giphyMatch[1]}/giphy.gif`}
          alt="Giphy"
          className="max-h-64 rounded-xl"
          loading="lazy"
        />
      </div>
    );
  }

  if (IMAGE_RE.test(url)) {
    return (
      <div className="forum-embed forum-embed--image">
        <img src={url} alt="" className="max-h-96 rounded-xl object-contain" loading="lazy" />
      </div>
    );
  }

  return null;
}

/** Scans text for embeddable URLs and renders them below the body. */
export function InlineEmbeds({ text }: { text: string }) {
  const urlRe = /https?:\/\/[^\s<>"]+/g;
  const urls = Array.from(new Set(text.match(urlRe) ?? [])).slice(0, 3);
  const embeddable = urls.filter(
    (u) => YOUTUBE_RE.test(u) || GIPHY_RE.test(u) || IMAGE_RE.test(u),
  );
  if (!embeddable.length) return null;
  return (
    <div className="mt-3 space-y-3">
      {embeddable.map((u) => <MediaEmbed key={u} url={u} />)}
    </div>
  );
}
