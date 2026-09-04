import type { MetadataRoute } from "next";
import { SITE_URL } from "./layout";

/** Nothing here is private, and a real domain should say where its sitemap lives. */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/" },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
