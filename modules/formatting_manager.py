import tkinter as tk
import re

class FormattingManager:
    def __init__(self):
        self.inline_markers = {
            'bold': '*B*',
            'italic': '*I*',
            'underline': '*U*'
        }
        self.paragraph_markers = {
            'heading': ('###', '###'),
            'centered': ('{', '}'),
            'right_aligned': ('>>>', '<<<')
        }
        self.all_markers_regex = re.compile(r'(\*B\*|\*I\*|\*U\*|###|\{|\}|>>>|<<<)')

    def get_combined_tag(self, tags_set):
        """Get the combined tag name from a set of tags for Tkinter."""
        if not tags_set:
            return None
        parts = []
        if 'bold' in tags_set: parts.append('bold')
        if 'italic' in tags_set: parts.append('italic')
        if 'underline' in tags_set: parts.append('underline')
        return '_'.join(parts)

    def insert_formatted_text(self, text_widget, text: str):
        """Insert raw text with markers into a Tkinter Text widget with tags."""
        pattern = re.compile(r'(\*B\*|\*I\*|\*U\*)')
        active_tags_set = set()
        last_pos = 0
        
        for match in pattern.finditer(text):
            start = match.start()
            if start > last_pos:
                segment = text[last_pos:start]
                if segment:
                    tag_name = self.get_combined_tag(active_tags_set)
                    text_widget.insert(tk.END, segment, (tag_name,) if tag_name else ())
            
            marker = match.group(1)
            tag = next((t for t, m in self.inline_markers.items() if m == marker), None)
            if tag:
                if tag in active_tags_set:
                    active_tags_set.remove(tag)
                else:
                    active_tags_set.add(tag)
            
            last_pos = match.end()
            
        if last_pos < len(text):
            segment = text[last_pos:]
            if segment:
                tag_name = self.get_combined_tag(active_tags_set)
                text_widget.insert(tk.END, segment, (tag_name,) if tag_name else ())

    def convert_text_to_raw_content(self, text_widget) -> str:
        """Converts the content of the Text widget back to raw format with markers, handling nested formats correctly."""
        raw_lines = []
        
        last_line_index = text_widget.index('end-1c').split('.')[0]
        total_lines = int(last_line_index)

        # Define a specific order for inline tags to ensure consistent nesting
        ordered_inline_tags = ['bold', 'italic', 'underline']

        for line_num in range(1, total_lines + 1):
            line_start = f"{line_num}.0"
            line_end = f"{line_num}.end"
            line_text = text_widget.get(line_start, line_end)
            
            if not line_text:
                raw_lines.append("")
                continue

            raw_line = ""
            prev_tags = set()
            
            for i, char in enumerate(line_text):
                index = f"{line_num}.{i}"
                
                # Get all tags and parse combined tags like 'bold_italic'
                raw_tags = text_widget.tag_names(index)
                current_tags = set()
                for raw_tag in raw_tags:
                    current_tags.update(tag for tag in raw_tag.split('_') if tag in self.inline_markers)

                if current_tags != prev_tags:
                    # Tags to close (were in prev but not in current)
                    tags_to_close = prev_tags - current_tags
                    for tag in reversed(ordered_inline_tags): # Close in reverse order of opening
                        if tag in tags_to_close:
                            raw_line += self.inline_markers[tag]

                    # Tags to open (are in current but not in prev)
                    tags_to_open = current_tags - prev_tags
                    for tag in ordered_inline_tags:
                        if tag in tags_to_open:
                            raw_line += self.inline_markers[tag]
                
                raw_line += char
                prev_tags = current_tags

            # Close any remaining open tags at the end of the line
            for tag in reversed(ordered_inline_tags):
                if tag in prev_tags:
                    raw_line += self.inline_markers[tag]

            # Handle paragraph-level tags
            line_tags = text_widget.tag_names(line_start)
            for tag, (start_marker, end_marker) in self.paragraph_markers.items():
                if tag in line_tags:
                    raw_line = f"{start_marker}{raw_line}{end_marker}"
                    break
            
            raw_lines.append(raw_line)
            
        return "\n".join(raw_lines)
