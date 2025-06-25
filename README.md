```markdown
# Digital Prison Reporting - Releases

This repository orchestrates the deployment of digital prison reporting components using **CircleCI**, based on YAML configuration files located in `prod/` and `preprod/` directories.

It enables dynamic and flexible promotion of services, lambdas, domains, and other artifacts across environments using a parameterized CI/CD setup.

---

## Repository Structure

```

.
├── preprod/                            # Pre-production release definitions
│   ├── digital-prison-reporting-jobs.yml
│   ├── digital-prison-reporting-thirdparty-components.yml
│   └── ...
├── prod/                               # Production release definitions
│   ├── digital-prison-reporting-jobs.yml
│   ├── digital-prison-reporting-thirdparty-components.yml
│   └── ...
├── .circleci/
│   ├── config.yml                      # Setup workflow to parse changes and launch main pipeline
│   └── main.yml                        # Main CircleCI pipeline with generic release logic
└── README.md

```

---

---

### Executor & Tag Mapping (Update in your YAML)

Use the following table to determine the correct `executor` and `tag` based on the job type or component. These values must go inside the `release.executor` section of your `prod/*.yml` or `preprod/*.yml` files.

| Job Type / Component                | project_key            | executor               | tag                        | Notes                               |
|------------------------------------|-------------------------|------------------------|-----------------------------|--------------------------------------|
| Reporting Jobs                     | `gradle`                | `reporting/java`       | `8.0`                       | Legacy reporting batch jobs          |
| Scheduled Dataset Lambda           | `gradle`                | `reporting/java`       | `21.0`                      | e.g. `digital-prison-reporting-scheduled-dataset-lambda.yml` |
| Multiphase Query / Cleanup Lambda  | `gradle`                | `reporting/java`       | `21.0`                      | Lambda-based Spark SQL jobs          |
| Terraform Components               | `terraform`             | `reporting/terraform-aws` | `v1.10.0-awscliv1-1.0.2` | Used for IaC and DMS provisioning    |
| Flyway Migration                   | `flyway`                | `reporting/aws`        | `2023.12.1`                 | Flyway DB migrations                 |
| Third-Party Artifacts              | `thirdparty_artifacts`  | `reporting/base`       | `3.10`                      | For artifact bundling and publishing |
| Other / Default Java Jobs          | `gradle`                | `reporting/java`       | `11.0` (default fallback)   | If job type not matched above        |

---

💡 **Note**: Ensure your YAML structure follows this nested format:

```yaml
release:
  project: digital-prison-reporting-xyz
  release_type: thirdparty_artifacts
  tag: v0.0.1
  executor:
    name: reporting/base
    tag: 3.10

---

## CircleCI Workflow Overview

1. **Setup Workflow (`.circleci/config.yml`)**
   - Detects changes to `prod/*.yml` or `preprod/*.yml`
   - Infers the target project from the changed file name
   - Parses executor/tag/project_key dynamically using [`yq`](https://github.com/mikefarah/yq)
   - Builds a `params.json` file
   - Launches the actual pipeline using `continuation/continue`

2. **Main Workflow (`.circleci/main.yml`)**
   - Uses pipeline parameters (`executor`, `tag`, `project_key`, etc.)
   - Triggers a shared orb job `reporting/generic_release`
   - Supports full releases, dry runs, and artifact sync

---

## Defining a New Release

To add a new component for deployment:

1. Create a new YAML file in either `prod/` or `preprod/`, for example:
```

preprod/my-new-service.yml

````

2. Use the following template:

```yaml
release:
  project: my-new-service
  release_type: backend | lambda | thirdparty_artifacts | terraform
  release_category: backend
  tag: v1.0.0
  executor:
    name: reporting/java
    tag: 17.0
  extra_args:
    jars_path: jars
    zips_path: zips
    s3_bucket_prefix: dpr-artifact-store
    yaml_path: configs
````

3. Commit and push your changes. The pipeline will:

   * Detect the change
   * Extract metadata from your YAML
   * Trigger the deployment pipeline accordingly

---

## Local Testing

You can verify YAML structure and debugging with:

```bash
yq e '.release.executor.name' preprod/my-new-service.yml
```

Make sure your file follows the nested structure required for `yq` v4.

---

## Troubleshooting

* **Q: Pipeline exits with `executor: null` or `tag: null`**

  * Make sure your `executor` is nested under `.release.executor`, not top-level.
  * Validate using: `yq e '.release.executor.tag' file.yml`

* **Q: Pipeline exits with `skip: true`**

  * Likely no matching project was detected or `project.yml` not found.
  * Make sure changes are made under `prod/` or `preprod/`

* **Q: `yq` command not found**

  * This is automatically installed inside the `clone` job via GitHub binary.
  * No manual setup needed.

---

## Maintainers

* Platform Engineering Team —  HMPPS DPR TEAM
* Slack: #ask-dpr

---
