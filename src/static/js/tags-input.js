/**
 * Tags input component with autocomplete
 *
 * Converts a regular text input into a tag selector with:
 * - Visual tag chips
 * - Autocomplete from existing tags
 * - Support for creating new tags
 */

class TagsInput {
    constructor(inputElement) {
        this.input = inputElement;
        this.selectedTags = [];
        this.availableTags = [];
        this.container = null;
        this.autocompleteList = null;

        this.init();
    }

    async init() {
        // Fetch existing tags
        await this.fetchTags();

        // Parse initial tags from input value
        if (this.input.value) {
            this.selectedTags = this.input.value
                .split(',')
                .map(t => t.trim())
                .filter(t => t);
        }

        // Create UI
        this.createUI();

        // Hide original input
        this.input.style.display = 'none';
    }

    async fetchTags() {
        try {
            const response = await fetch('/tags');
            if (response.ok) {
                const tags = await response.json();
                this.availableTags = tags.map(t => t.name);
            }
        } catch (error) {
            console.error('Failed to fetch tags:', error);
        }
    }

    createUI() {
        // Create container
        this.container = document.createElement('div');
        this.container.className = 'tags-input-container';

        // Create tag chips container
        const chipsContainer = document.createElement('div');
        chipsContainer.className = 'tags-chips';
        this.container.appendChild(chipsContainer);

        // Create input for new tags
        const newTagInput = document.createElement('input');
        newTagInput.type = 'text';
        newTagInput.className = 'tags-new-input';
        newTagInput.placeholder = 'Type to add tags...';
        this.container.appendChild(newTagInput);

        // Create autocomplete list
        this.autocompleteList = document.createElement('div');
        this.autocompleteList.className = 'tags-autocomplete';
        this.autocompleteList.style.display = 'none';
        this.container.appendChild(this.autocompleteList);

        // Insert after original input
        this.input.parentNode.insertBefore(this.container, this.input.nextSibling);

        // Render initial tags
        this.renderTags();

        // Event listeners
        newTagInput.addEventListener('input', (e) => this.onInput(e));
        newTagInput.addEventListener('keydown', (e) => this.onKeyDown(e));
        newTagInput.addEventListener('blur', () => {
            // Delay hiding to allow click on autocomplete
            setTimeout(() => this.hideAutocomplete(), 200);
        });
    }

    renderTags() {
        const chipsContainer = this.container.querySelector('.tags-chips');
        chipsContainer.innerHTML = '';

        this.selectedTags.forEach(tag => {
            const chip = document.createElement('span');
            chip.className = 'tag-chip';
            chip.innerHTML = `
                ${tag}
                <button type="button" class="tag-remove" data-tag="${tag}">&times;</button>
            `;
            chip.querySelector('.tag-remove').addEventListener('click', () => this.removeTag(tag));
            chipsContainer.appendChild(chip);
        });

        // Update hidden input
        this.input.value = this.selectedTags.join(', ');
    }

    onInput(e) {
        const value = e.target.value.trim().toLowerCase();

        if (value.length === 0) {
            this.hideAutocomplete();
            return;
        }

        // Filter available tags that aren't already selected
        const suggestions = this.availableTags
            .filter(tag =>
                tag.toLowerCase().includes(value) &&
                !this.selectedTags.includes(tag)
            )
            .slice(0, 10); // Limit to 10 suggestions

        this.showAutocomplete(suggestions, value);
    }

    onKeyDown(e) {
        const input = e.target;

        if (e.key === 'Enter' || e.key === ',') {
            e.preventDefault();
            const value = input.value.trim().toLowerCase();
            if (value) {
                this.addTag(value);
                input.value = '';
                this.hideAutocomplete();
            }
        } else if (e.key === 'Backspace' && input.value === '' && this.selectedTags.length > 0) {
            // Remove last tag when backspace on empty input
            this.removeTag(this.selectedTags[this.selectedTags.length - 1]);
        }
    }

    addTag(tag) {
        const normalizedTag = tag.toLowerCase().trim();
        if (normalizedTag && !this.selectedTags.includes(normalizedTag)) {
            this.selectedTags.push(normalizedTag);
            this.renderTags();
        }
    }

    removeTag(tag) {
        this.selectedTags = this.selectedTags.filter(t => t !== tag);
        this.renderTags();
    }

    showAutocomplete(suggestions, currentInput) {
        if (suggestions.length === 0) {
            this.hideAutocomplete();
            return;
        }

        this.autocompleteList.innerHTML = '';
        suggestions.forEach(tag => {
            const item = document.createElement('div');
            item.className = 'tags-autocomplete-item';
            item.textContent = tag;
            item.addEventListener('mousedown', () => {
                this.addTag(tag);
                this.container.querySelector('.tags-new-input').value = '';
                this.hideAutocomplete();
            });
            this.autocompleteList.appendChild(item);
        });

        this.autocompleteList.style.display = 'block';
    }

    hideAutocomplete() {
        this.autocompleteList.style.display = 'none';
    }
}

// CSS styles
const style = document.createElement('style');
style.textContent = `
.tags-input-container {
    position: relative;
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 8px;
    background: white;
    min-height: 42px;
}

.tags-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 6px;
}

.tag-chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: #4db8ba;
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 14px;
}

.tag-remove {
    background: none;
    border: none;
    color: white;
    font-size: 18px;
    line-height: 1;
    cursor: pointer;
    padding: 0;
    margin-left: 4px;
}

.tag-remove:hover {
    color: #ff6600;
}

.tags-new-input {
    border: none;
    outline: none;
    font-size: 15px;
    font-family: inherit;
    padding: 4px;
    flex: 1;
    min-width: 120px;
}

.tags-autocomplete {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: white;
    border: 1px solid #ccc;
    border-top: none;
    border-radius: 0 0 4px 4px;
    max-height: 200px;
    overflow-y: auto;
    z-index: 1000;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.tags-autocomplete-item {
    padding: 8px 12px;
    cursor: pointer;
    font-size: 14px;
}

.tags-autocomplete-item:hover {
    background: #f0f0f0;
}
`;
document.head.appendChild(style);
