import type { MetadataRoute } from "next";
import { SITE_URL } from "./layout";

/** One page, so one entry. Kept as a file rather than hand-written XML so it cannot
 *  disagree with the domain the rest of the metadata uses. */
export default function sitemap(): MetadataRoute.Sitemap {
  return [{ url: SITE_URL, lastModified: new Date(), changeFrequency: "weekly", priority: 1 }];
}
