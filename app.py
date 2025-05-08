st.markdown("""
<style>
    .selected-card {
        background-color: #e8f4f8;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        display: flex;
        align-items: center;
        gap: 15px;
        border-left: 5px solid #3498db;
    }
    .selected-char { font-size: 2.5em; color: #e74c3c; margin: 0; }
    .clickable-char {
        cursor: pointer;
        color: #e74c3c;
        transition: color 0.2s;
    }
    .clickable-char:hover {
        color: #c0392b;
        text-decoration: underline;
    }
    .details { font-size: 1.1em; color: #34495e; margin: 0; }
    .details strong { color: #2c3e50; }
    .results-header { font-size: 1.5em; color: #2c3e50; margin: 20px 0 10px; }
    .char-card {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    .char-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 3px 8px rgba(0,0,0,0.15);
    }
    .char-title { font-size: 1.4em; color: #e74c3c; margin: 0; display: inline; }
    .compounds-section {
        background-color: #f1f8e9;
        padding: 10px;
        border-radius: 5px;
        margin-top: 10px;
    }
    .compounds-title { font-size: 1.1em; color: #558b2f; margin: 0 0 5px; }
    .compounds-list { font-size: 1em; color: #34495e; margin: 0; }
    @media (max-width: 768px) {
        .selected-card { flex-direction: column; align-items: flex-start; padding: 10px; }
        .selected-char { font-size: 2em; }
        .details, .compounds-list { font-size: 0.95em; line-height: 1.5; }
        .results-header { font-size: 1.3em; }
        .char-card { padding: 10px; }
        .char-title { font-size: 1.2em; }
        .compounds-title { font-size: 1em; }
    }
</style>
""", unsafe_allow_html=True)
