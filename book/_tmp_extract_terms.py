import re
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

p = Path(__file__).with_name("curriculum.yaml")
text = p.read_text(encoding="utf-8")

# Prefer YAML parse; fall back to title lines
titles = []
if yaml:
    data = yaml.safe_load(text)
    for c in data.get("courses", []):
        if c.get("title"):
            titles.append(c["title"])
        for lec in c.get("lectures") or []:
            if lec.get("title"):
                titles.append(lec["title"])
else:
    titles = re.findall(r'^\s+title:\s+[\'"]?(.+?)[\'"]?\s*$', text, re.M)

known = [
    "Git", "GitHub", "GitLab", "GitOps", "SQL", "NoSQL", "MySQL", "PostgreSQL",
    "Postgres", "MongoDB", "Redis", "Kafka", "RabbitMQ", "Kubernetes", "kubectl",
    "nginx", "Nginx", "Terraform", "Docker", "AWS", "GCP", "Azure", "HTTP",
    "HTTPS", "DNS", "TLS", "SSL", "JWT", "OAuth", "OIDC", "GraphQL", "gRPC",
    "REST", "CRUD", "ACID", "CAP", "JSON", "YAML", "TOML", "XML", "HTML",
    "CSS", "API", "CLI", "SDK", "CI", "CD", "CI/CD", "DevOps", "SaaS", "PaaS",
    "IaaS", "LLM", "RAG", "MCP", "eBPF", "WASM", "WebAssembly", "Next.js",
    "Node.js", "Vue", "React", "Angular", "TypeScript", "JavaScript",
    "ClickHouse", "Elasticsearch", "Prometheus", "Grafana", "Jenkins",
    "Ansible", "Pulumi", "Istio", "Envoy", "etcd", "DynamoDB", "Firestore",
    "BigQuery", "OpenTelemetry", "OTel", "Jaeger", "Sentry", "Datadog",
    "Playwright", "Cypress", "Vitest", "Webpack", "Vite", "npm", "pnpm",
    "Bun", "Deno", "Prisma", "Django", "Flask", "FastAPI", "Spring",
    "Laravel", "Rails", "Elixir", "Kotlin", "Swift", "Rust", "Python",
    "Java", "C++", "C#", ".NET", "Linux", "Unix", "Windows", "macOS", "WSL",
    "SSH", "VPN", "CDN", "S3", "EC2", "IAM", "VPC", "EKS", "ECS", "Lambda",
    "Fargate", "CloudFormation", "Helm", "Argo", "ArgoCD", "Flux",
    "Kustomize", "Podman", "Compose", "Nomad", "Consul", "Vault", "Celery",
    "Temporal", "Debezium", "Parquet", "Protobuf", "Avro", "Thrift",
    "WebSocket", "WebRTC", "CORS", "CSRF", "XSS", "OWASP", "RBAC", "mTLS",
    "SLA", "SLO", "SLI", "MTTR", "SemVer", "UUID", "GUID", "CIDR", "NAT",
    "DHCP", "TCP", "UDP", "IPv4", "IPv6", "QUIC", "HTTP/2", "HTTP/3", "SSR",
    "CSR", "SSG", "ISR", "SPA", "PWA", "DOM", "AST", "BFF", "nginx",
    "Memcached", "SQLite", "Cassandra", "ScyllaDB", "Neo4j", "Elastic",
    "Kibana", "Logstash", "Fluentd", "Fluent Bit", "Loki", "Tempo", "Thanos",
    "Nginx", "HAProxy", "Traefik", "Caddy", "Kong", "Envoy", "Linkerd",
    "Cilium", "containerd", "runc", "systemd", "journalctl", "chmod", "sudo",
    "regex", "NaN", "null", "undefined", "boolean", "enum", "struct", "tuple",
    "hashmap", "btree", "B-tree", "LSM", "WAL", "MVCC", "JSONB", "GIN",
    "GiST", "BRIN", "HNSW", "FAISS", "pgvector", "LangChain", "LlamaIndex",
    "Pinecone", "Weaviate", "Chroma", "Supabase", "Firebase", "Vercel",
    "Netlify", "Heroku", "Cloudflare", "Tailscale", "WireGuard", "ngrok",
    "Postman", "Insomnia", "Swagger", "OpenAPI", "AsyncAPI", "tRPC",
    "Axios", "Zustand", "Redux", "Pinia", "Vuex", "TanStack", "SWR",
    "Tailwind", "Bootstrap", "shadcn", "Radix", "Framer", "Three.js",
    "WebGL", "WebGPU", "LLVM", "Clang", "GCC", "QEMU", "Hyper-V", "KVM",
    "VirtualBox", "VMware", "Homebrew", "Chocolatey", "winget", "apt",
    "yum", "pacman", "Nix", "asdf", "nvm", "pyenv", "rustup", "cargo",
    "poetry", "pipenv", "uv", "conda", "pytest", "Jest", "Mocha", "JUnit",
    "Mockito", "Cucumber", "Selenium", "Puppeteer", "k6", "JMeter",
    "Gatling", "Locust", "Artillery", "Wireshark", "tcpdump", "openssl",
    "certbot", "GPG", "PGP", "SOPS", "Trivy", "Snyk", "Dependabot",
    "Renovate", "Semgrep", "CodeQL", "SonarQube", "ESLint", "Prettier",
    "Black", "Ruff", "mypy", "Pyright", "tsc", "Babel", "SWC", "esbuild",
    "Rollup", "Parcel", "Turbopack", "Nx", "Turborepo", "Bazel", "Maven",
    "Gradle", "Ant", "Make", "CMake", "Ninja", "Meson", "SCons", "Buck",
    "Pants", "Please", "Just", "Task", "Invoke", "Tox", "Nox", "Hatch",
    "PDM", "Rye", "Pixi", "Mamba", "Micromamba", "Pixi", "Poetry",
]

found = set()
blob = "\n".join(titles)
for term in known:
    if re.search(rf"(?i)\b{re.escape(term)}\b", blob) or term in blob:
        found.add(term)

# Also scan titles for ALLCAPS / CamelTech tokens
for t in titles:
    for w in re.findall(r"[A-Za-z][A-Za-z0-9+#./-]{1,}", t):
        if w.isupper() and 2 <= len(w) <= 8:
            found.add(w)
        if any(ch in w for ch in "#+/.") and len(w) > 1:
            found.add(w)

print("=== Lecture / course titles mentioning tech ===")
for t in titles:
    print(f"- {t}")

print(f"\n=== Matched known terms ({len(found)}) ===")
for w in sorted(found, key=str.lower):
    print(w)
