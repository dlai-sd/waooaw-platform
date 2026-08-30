// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Content And Internal Linking
// Constitutional basis: C-002 (Evidence Integrity), C-059 (Implementation Traceability)
import { getPublishedArticle, listPublishedArticles } from './blogs';
describe('public article catalogue', () => {
  it('contains only published articles with real dates', () => expect(listPublishedArticles().every((article) => article.state === 'published' && Boolean(article.modifiedAt))).toBe(true));
  it('returns no publication for unknown slugs', () => expect(getPublishedArticle('draft-or-missing')).toBeUndefined());
});