#!/bin/bash

set -e

README_FILE="README.md"

# Function to extract release info and last updated date
extract_release_info() {
  folder=$1
  find "$folder" -type f -name "*.yml" | while read -r file; do
    project=$(yq e '.release.project' "$file")
    tag=$(yq e '.release.tag' "$file")
    last_updated=$(git log -1 --format="%ad" --date=short -- "$file")

    if [[ "$project" != "null" && "$tag" != "null" ]]; then
      echo "| $project | $tag | $folder | $last_updated |"
    fi
  done
}

# Generate release history table
release_table=$(cat <<EOF
<!-- RELEASE_HISTORY_START -->
| Project                         | Tag       | Environment | Last Updated |
|---------------------------------|-----------|-------------|---------------|
$(extract_release_info "prod")
$(extract_release_info "preprod")
<!-- RELEASE_HISTORY_END -->
EOF
)

# Replace block in README
perl -0777 -i -pe "s/<!-- RELEASE_HISTORY_START -->.*?<!-- RELEASE_HISTORY_END -->/$release_table/s" "$README_FILE"

echo "✅ README.md updated with release history (no commit)."
