# cintnet.org ORG site

The foundation site: vision, research, labs, blog, about, get involved and policy pages. Specs: `specs\03-SITEMAP-AND-PAGE-SCHEMATICS-SPEC.md`, `specs\org\requirements-and-tasks.md`, and the voice guide `specs\org\voice.md`.

## Layout

- `content/` holds one HTML fragment per page, with front-matter (`title`, `description`, `reader`, `takeaway`, `template`; articles also need `date`, `category`, `minutes`, `lede`).
- `assets/` holds CSS, JS (progressive enhancement only; the site works without it) and illustrations.
- `build.py` renders everything into `dist/` and fails on: missing front-matter, money, token or royalty claims, internal codes, research jargon outside "For researchers" asides, broken internal links and unsafe JS.

## Commands

```
python site/build.py              # build and check
python site/build.py --serve      # build, then preview at http://localhost:8080
python -m unittest discover -s site
```

## Adding a blog post

Copy an existing file in `content/blog/`, keep its front-matter fields, write to the voice guide, and run the build. Posts go through the Spec 09 writing pipeline, and the steward approves each one before publishing.

## Cutover (steward gate, not done yet)

1. Add a hosting target for `site/dist`, for example `"target": "org", "public": "site/dist"` in `firebase.json`, and map it to the site currently serving `cintnet.org` in `.firebaserc`.
2. Preview first: `firebase hosting:channel:deploy preview --only org`.
3. Create a new Firebase hosting site for `horizon.cintnet.org`, move the frozen portal there under `/legacy/`, and add the custom domain (DNS record).
4. Deploy `org` to `cintnet.org`.
