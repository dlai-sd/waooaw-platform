// Implements: architecture/reference/ux/hybrid-application-shell.md §Route and Layout Ownership
// Constitutional basis: C-059 (Implementation Traceability)

import type { Metadata } from 'next';
import { listPublishedArticles } from '@/config/blogs';
import { publicMetadata } from '@/lib/public-seo';

export const metadata: Metadata = publicMetadata('Insights | WAOOAW', 'Research and practical guidance about governed digital professionals.', '/blogs');

export default function BlogsPage() {
	return <div className="public-document article-index"><header><p className="eyebrow">Research and guidance</p><h1>Insights</h1><p>Practical thinking about governed autonomy, evidence, and professional work.</p></header>{listPublishedArticles().map((article) => <article key={article.slug}><p className="eyebrow">{article.category}</p><h2><a href={`/blogs/${article.slug}`}>{article.title}</a></h2><p>{article.description}</p><time dateTime={article.publishedAt}>{article.publishedAt}</time></article>)}</div>;
}