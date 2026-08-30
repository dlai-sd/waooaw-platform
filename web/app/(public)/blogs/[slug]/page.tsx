// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Content And Internal Linking
// Constitutional basis: C-002 (Evidence Integrity), C-059 (Implementation Traceability)

import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { StructuredData } from '@/components/public/StructuredData';
import { getPublishedArticle, listPublishedArticles } from '@/config/blogs';
import { absoluteUrl, siteConfig } from '@/config/site';
import { breadcrumbData, publicMetadata } from '@/lib/public-seo';

export const dynamicParams = false;
export function generateStaticParams() { return listPublishedArticles().map(({ slug }) => ({ slug })); }
export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> { const article = getPublishedArticle((await params).slug); if (!article) notFound(); return publicMetadata(`${article.title} | WAOOAW`, article.description, `/blogs/${article.slug}`, 'article'); }
export default async function BlogArticlePage({ params }: { params: Promise<{ slug: string }> }) { const article = getPublishedArticle((await params).slug); if (!article) notFound(); const path = `/blogs/${article.slug}`; return <article className="public-document blog-detail"><StructuredData value={[{ '@context': 'https://schema.org', '@type': 'Article', headline: article.title, description: article.description, datePublished: article.publishedAt, dateModified: article.modifiedAt, mainEntityOfPage: absoluteUrl(path), author: { '@type': 'Organization', name: siteConfig.name } }, breadcrumbData(article.title, path)]} /><header><p className="eyebrow">{article.category}</p><h1>{article.title}</h1><p>{article.description}</p><time dateTime={article.publishedAt}>Published {article.publishedAt}</time></header>{article.paragraphs.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}<a className="primary-link" href={`/professionals/${article.relatedProfessional}`}>Explore the related professional</a></article>; }