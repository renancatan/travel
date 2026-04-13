# Architecture

## Product Shape

The new app is not a general travel social network in v1. It is a focused travel media workflow:

1. ingest trip media
2. extract metadata
3. score and group assets
4. propose social-ready outputs
5. let the user approve
6. update the travel map
7. optionally prepare or publish social content

## Core Services

### Web App

Responsibilities:

- upload media
- review AI suggestions
- approve final selections
- manage map entries
- preview exported deliverables

### API Service

Responsibilities:

- albums and trips
- media item metadata
- map entry records
- selection sessions
- user decisions and feedback
- job dispatching

### Media Worker

Responsibilities:

- metadata extraction
- near-duplicate detection
- aesthetic and utility scoring
- clip extraction
- image/video derivative generation
- export packaging

## Core Domain Objects

- `Trip`
- `Album`
- `MediaItem`
- `MediaGroup`
- `SelectionSession`
- `ExportArtifact`
- `MapEntry`

## Provider Boundaries

Keep these interfaces explicit so the app can move off AWS later without rewriting the domain logic:

- `StorageProvider`
- `JobQueue`
- `MediaAnalyzer`
- `CaptionGenerator`
- `SocialPublisher`
- `LocationResolver`

## AWS-First Mapping

- `StorageProvider` -> Amazon S3
- `JobQueue` -> Amazon SQS
- `API/Web` -> container deployment
- `Metadata DB` -> Postgres
- `CDN` -> optional CloudFront later

## Portability Rule

AWS-specific code should stay in infrastructure adapters only. The core logic should not know whether a file lives in S3, R2, or local disk.

