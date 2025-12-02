import streamlit as st
import pandas as pd
import openai
import subprocess
import tempfile
import os
import warnings
import datetime
import base64
from io import BytesIO
import json
import re
import sys

st.set_page_config(
    page_title="Ask Your CSV (R Edition)",
    page_icon="📊",
    layout="wide"
)

# Initialize OpenAI client
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Helper function to fix common R path issues
def fix_r_code(code, error_msg):
    """Attempt to fix common R code errors"""
    fixed_code = code
    
    # Fix Windows path issues (backslashes)
    if "\\U" in error_msg or "\\u" in error_msg or "used without hex digits" in error_msg:
        # Replace single backslashes with forward slashes or double backslashes
        import re
        # This shouldn't happen in our generated code, but just in case
        fixed_code = fixed_code.replace("\\", "/")
    
    return fixed_code

# Helper function to run R code
# --- CẬP NHẬT ĐOẠN NÀY TRONG APP.PY ---

# --- Thay thế đoạn code tương ứng trong app.py của bạn ---

def get_r_path():
    """
    Tìm đường dẫn tuyệt đối của Rscript dựa trên vị trí Python.
    Đây là cách duy nhất hoạt động ổn định trên Streamlit Cloud Conda.
    """
    # 1. Lấy thư mục chứa file python hiện tại (VD: /home/user/.conda/envs/env/bin)
    python_dir = os.path.dirname(sys.executable)
    
    # 2. Tạo đường dẫn tuyệt đối tới Rscript
    r_path = os.path.join(python_dir, "Rscript")
    
    # 3. Kiểm tra tồn tại
    if os.path.exists(r_path):
        return r_path
    
    # Fallback: Nếu chạy local trên Windows thì có thể là Rscript.exe
    if os.path.exists(r_path + ".exe"):
        return r_path + ".exe"
        
    # Fallback cuối cùng: Thử các đường dẫn Linux tiêu chuẩn
    if os.path.exists("/usr/bin/Rscript"): return "/usr/bin/Rscript"
    if os.path.exists("/usr/local/bin/Rscript"): return "/usr/local/bin/Rscript"
    
    return None

def check_r_environment():
    """Kiểm tra R có chạy được không bằng đường dẫn tuyệt đối"""
    r_path = get_r_path()
    
    if not r_path:
        return False, f"❌ Cannot find Rscript. Python is at: {sys.executable}"
        
    try:
        # Lưu đường dẫn tìm được vào session state để dùng cho các hàm khác
        st.session_state['r_path'] = r_path
        
        result = subprocess.run(
            [r_path, '--version'], # <--- Dùng đường dẫn tuyệt đối
            capture_output=True,
            text=True,
            timeout=5
        )
        return True, result.stderr
    except Exception as e:
        return False, str(e)

# --- CẬP NHẬT HÀM NÀY ĐỂ FIX LỖI PANDOC ---
def run_r_code(code, df, output_dir):
    """Execute R code and return results"""
    # 1. Chuẩn bị dữ liệu
    csv_path = os.path.join(output_dir, "temp_data.csv")
    df.to_csv(csv_path, index=False)
    
    csv_path_r = csv_path.replace("\\", "/")
    output_dir_r = output_dir.replace("\\", "/")
    
    # 2. Tự động tìm đường dẫn thư mục bin của Conda (Nơi chứa Pandoc)
    # Vì Python, R, và Pandoc cùng nằm trong 1 thư mục bin của Conda
    conda_bin_dir = os.path.dirname(sys.executable)
    
    # 3. Tạo R Script với cấu hình Pandoc cưỡng bức
    r_script = f"""
# --- CONFIG PANDOC (BẮT BUỘC) ---
# Ép R tìm Pandoc trong cùng thư mục với Python/R
conda_dir <- "{conda_bin_dir}"
Sys.setenv(RSTUDIO_PANDOC = conda_dir)
Sys.setenv(PATH = paste(conda_dir, Sys.getenv("PATH"), sep=":"))

# Setup working dir
setwd("{output_dir_r}")
df <- read.csv("{csv_path_r}")

# Load Libraries
suppressPackageStartupMessages({{
    library(ggplot2)
    library(dplyr)
    library(gtsummary)
    library(survival)
    library(survminer)
    library(flextable)
    library(broom.helpers) # Đã cài thêm
}})

# User Code
{code}
"""
    
    script_path = os.path.join(output_dir, "script.R")
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(r_script)
    
    # 4. Tìm R executable (như logic cũ)
    r_exec = st.session_state.get('r_path')
    if not r_exec: 
        r_exec = get_r_path() # Hàm này bạn đã có ở bước trước
    
    if not r_exec:
        return {
            'success': False, 
            'stderr': 'CRITICAL: Rscript not found.',
            'code': code
        }

    try:
        # Run R script
        result = subprocess.run(
            [r_exec, script_path],
            capture_output=True,
            text=True,
            timeout=120, # Tăng timeout lên 2 phút cho chắc
            cwd=output_dir
        )
        
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'output_dir': output_dir,
            'code': code
        }
    except Exception as e:
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'output_dir': output_dir,
            'code': code
        }

# Helper function to extract HTML tables from R output
def extract_html_from_output(output_dir):
    """Extract HTML content from files in output directory"""
    html_files = []
    
    # Look for HTML files
    for file in os.listdir(output_dir):
        if file.endswith('.html'):
            file_path = os.path.join(output_dir, file)
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
                
                # Extract style and table content from the full HTML
                # gtsave creates a complete HTML document, we need just the table part
                style_match = re.search(r'<style>(.*?)</style>', html_content, re.DOTALL)
                table_match = re.search(r'<div id="[^"]*"[^>]*>.*?<table.*?</table>.*?</div>', html_content, re.DOTALL)
                
                if style_match and table_match:
                    # Combine style and table
                    clean_html = f"<style>{style_match.group(1)}</style>\n{table_match.group(0)}"
                    html_files.append(clean_html)
                else:
                    # Fallback: use the full HTML content
                    html_files.append(html_content)
    
    return html_files

# Helper function to ask AI to fix R code
def get_fixed_r_code(original_code, error_msg, data_context):
    """Ask GPT to fix the R code based on error message"""
    fix_prompt = f"""The following R code produced an error. Please fix it and return ONLY the corrected R code without explanation.

Original code:
```r
{original_code}
```

Error message:
{error_msg}

Data context:
{data_context}

Requirements:
- Return ONLY valid R code in a ```r code block
- Fix the error but keep the same intent
- Use forward slashes (/) for any file paths
- Ensure all column names are correctly referenced
- The dataframe is called 'df'
- Libraries available: ggplot2, dplyr, gtsummary, survival, survminer, flextable
- For Kaplan-Meier plots, MUST load library(survminer) before using ggsurvplot()
- For ggsurvplot objects, save using: ggsave("plot.png", p$plot, width=10, height=6)
- For gtsummary tables, use correct syntax: as_flex_table(table) %>% save_as_html(path = "table.html")
- IMPORTANT: Always use pipe operator (%>%) and path parameter in save_as_html()
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an R debugging expert. Fix the code and return ONLY the corrected R code."},
                {"role": "user", "content": fix_prompt}
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        fixed_reply = response.choices[0].message.content
        
        # Extract code from response
        if "```r" in fixed_reply or "```R" in fixed_reply:
            code_blocks = fixed_reply.replace("```R", "```r").split("```r")
            if len(code_blocks) > 1:
                fixed_code = code_blocks[1].split("```")[0].strip()
                return fixed_code
        
        return None
    except Exception as e:
        st.warning(f"Could not auto-fix code: {str(e)}")
        return None

# Helper function to convert image to base64
def image_to_base64(image_path):
    """Convert image file to base64 string"""
    try:
        with open(image_path, 'rb') as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    except:
        return None

# Helper function for export
def export_conversation():
    """Export conversation history as HTML with images and tables"""
    if not st.session_state.messages:
        return None
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                margin: 40px; 
                background-color: #f9f9f9;
            }}
            h1 {{ 
                color: #333; 
                border-bottom: 3px solid #4CAF50;
                padding-bottom: 10px;
            }}
            h2 {{ 
                color: #666; 
                margin-top: 30px; 
                border-bottom: 1px solid #ddd;
                padding-bottom: 5px;
            }}
            .question {{ 
                background-color: #e3f2fd; 
                padding: 15px; 
                border-radius: 8px; 
                margin: 15px 0;
                border-left: 4px solid #2196F3;
            }}
            .answer {{ 
                background-color: #fff;
                padding: 15px; 
                margin: 15px 0;
                border-radius: 8px;
                border-left: 4px solid #4CAF50;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .metadata {{ 
                color: #999; 
                font-size: 14px; 
            }}
            .output-section {{
                background-color: #f5f5f5;
                padding: 10px;
                border-radius: 5px;
                margin: 10px 0;
            }}
            .output-label {{
                font-weight: bold;
                color: #555;
                margin-bottom: 5px;
            }}
            code {{ 
                background-color: #f5f5f5; 
                padding: 2px 4px; 
                border-radius: 3px;
                font-family: 'Courier New', monospace;
            }}
            pre {{ 
                background-color: #2d2d2d; 
                color: #f8f8f2;
                padding: 15px; 
                border-radius: 5px; 
                overflow-x: auto;
                font-family: 'Courier New', monospace;
            }}
            pre code {{
                background-color: transparent;
                color: #f8f8f2;
            }}
            .plot-image {{
                max-width: 100%;
                height: auto;
                margin: 15px 0;
                border-radius: 5px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            .table-container {{
                margin: 15px 0;
                overflow-x: auto;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 10px 0;
            }}
            .auto-fix-badge {{
                background-color: #ff9800;
                color: white;
                padding: 3px 8px;
                border-radius: 12px;
                font-size: 12px;
                margin-left: 10px;
            }}
        </style>
    </head>
    <body>
        <h1>📊 Data Analysis Report (R Edition)</h1>
        <p class="metadata">Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    """
    
    if st.session_state.df is not None:
        html_content += f"""
        <h2>📋 Dataset Information</h2>
        <ul>
            <li><strong>Total Rows:</strong> {st.session_state.df.shape[0]:,}</li>
            <li><strong>Total Columns:</strong> {st.session_state.df.shape[1]}</li>
            <li><strong>Column Names:</strong> {', '.join(st.session_state.df.columns)}</li>
        </ul>
        """
    
    html_content += "<h2>💬 Analysis Conversation</h2>"
    
    for idx, msg in enumerate(st.session_state.messages, 1):
        if msg["role"] == "user":
            html_content += f'<div class="question"><strong>❓ Question {idx//2 + 1}:</strong> {msg["content"]}</div>'
        else:
            # Add auto-fix badge if applicable
            fix_badge = ""
            if "fixed" in msg and msg["fixed"]:
                fix_badge = f'<span class="auto-fix-badge">✨ Auto-fixed after {msg["retries"]} attempt(s)</span>'
            
            content = msg["content"].replace("```r", "<pre><code class='language-r'>").replace("```", "</code></pre>")
            html_content += f'<div class="answer"><strong>💡 Analysis:</strong>{fix_badge}<br><br>{content}'
            
            # Add text output if exists
            if "output" in msg and msg["output"]:
                html_content += f'''
                <div class="output-section">
                    <div class="output-label">📄 R Console Output:</div>
                    <pre><code>{msg["output"]}</code></pre>
                </div>
                '''
            
            # Add executed R code if exists
            if "code" in msg:
                code_label = "📝 Executed R Code" if "error" not in msg else "⚠️ Failed R Code"
                code_class = "success" if "error" not in msg else "error"
                html_content += f'''
                <div class="output-section">
                    <div class="output-label">{code_label}:</div>
                    <pre><code class="language-r">{msg["code"]}</code></pre>
                </div>
                '''
                
                # Show error if exists
                if "error" in msg:
                    html_content += f'''
                    <div class="output-section" style="background-color: #ffebee;">
                        <div class="output-label" style="color: #c62828;">❌ Error Message:</div>
                        <pre><code>{msg["error"]}</code></pre>
                    </div>
                    '''
            
            # Add HTML tables if exists
            if "html_tables" in msg and msg["html_tables"]:
                html_content += '<div class="table-container">'
                html_content += '<div class="output-label">📊 Table Results:</div>'
                for table_html in msg["html_tables"]:
                    html_content += table_html
                html_content += '</div>'
            
            # Add plot images if exists (convert to base64)
            if "plot_images" in msg and msg["plot_images"]:
                html_content += '<div class="output-label">📈 Visualizations:</div>'
                for img_path in msg["plot_images"]:
                    if os.path.exists(img_path):
                        img_base64 = image_to_base64(img_path)
                        if img_base64:
                            html_content += f'<img src="data:image/png;base64,{img_base64}" class="plot-image" alt="Plot"/>'
            
            html_content += '</div>'
    
    html_content += """
    <hr style="margin-top: 40px;">
    <p class="metadata" style="text-align: center;">
        Generated by Ask Your CSV (R Edition) | Powered by R, ggplot2, gtsummary, and flextable
    </p>
    </body>
    </html>
    """
    
    return html_content

# Session state initialization
if "messages" not in st.session_state:
    st.session_state.messages = []
if "df" not in st.session_state:
    st.session_state.df = None
if "data_summary" not in st.session_state:
    st.session_state.data_summary = None

st.title("📊 Ask Your CSV (R Edition)")
st.markdown("Upload your data and ask questions in plain English - powered by R!")

# Sidebar for file upload
with st.sidebar:
    st.header("📁 Data Upload")
    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.session_state.df = df
            
            # Create data summary
            st.session_state.data_summary = {
                "shape": df.shape,
                "columns": df.columns.tolist(),
                "dtypes": df.dtypes.astype(str).to_dict(),
                "sample": df.head(3).to_dict(),
                "stats": df.describe().to_dict() if not df.empty else {}
            }
            
            st.success(f"✅ Loaded {df.shape[0]} rows × {df.shape[1]} columns")
            
            # Data preview
            with st.expander("Preview Data"):
                st.dataframe(df.head())
                
            # Basic stats
            with st.expander("Data Summary"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Rows", df.shape[0])
                    st.metric("Total Columns", df.shape[1])
                with col2:
                    st.metric("Memory Usage", f"{df.memory_usage().sum() / 1024:.1f} KB")
                    st.metric("Missing Values", df.isnull().sum().sum())
                    
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")
            st.info("Please make sure your file is a valid CSV format.")
    else:
        st.info("👆 Upload a CSV file to start analyzing!")
    
    # Export options
    if len(st.session_state.messages) >= 1:
        st.sidebar.markdown("---")
        st.sidebar.header("💾 Export Options")
        if st.sidebar.button("Generate Report"):
            export_html = export_conversation()
            st.sidebar.download_button(
                label="📥 Download Report (HTML)",
                data=export_html,
                file_name=f"data_analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.html",
                mime="text/html"
            )

# Main chat interface
if st.session_state.df is not None:
    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "fixed" in msg and msg["fixed"]:
                st.caption(f"✨ Auto-fixed after {msg['retries']} attempt(s)")
            
            # Show executed code for successful runs
            if "code" in msg and "error" not in msg:
                st.subheader("📝 Executed R Code", divider="green")
                st.code(msg["code"], language="r")
            
            # Show failed code
            if "code" in msg and "error" in msg:
                st.subheader("⚠️ Failed R Code", divider="red")
                st.code(msg["code"], language="r")
                st.error("Error:")
                st.code(msg["error"], language="text")
            
            if "output" in msg:
                st.text(msg["output"])
            if "html_tables" in msg:
                for html_content in msg["html_tables"]:
                    st.markdown(html_content, unsafe_allow_html=True)
            if "plot_images" in msg:
                for img_path in msg["plot_images"]:
                    if os.path.exists(img_path):
                        st.image(img_path)
    
    # Chat input
    user_input = st.chat_input("Ask a question about your data")
    
    if user_input:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Prepare data context
        df = st.session_state.df
        if len(df) > 100:
            data_context = f"""
            Dataset shape: {st.session_state.data_summary['shape']}
            Columns: {', '.join(st.session_state.data_summary['columns'])}
            Data types: {st.session_state.data_summary['dtypes']}
            Sample rows: {st.session_state.data_summary['sample']}
            Basic statistics: {st.session_state.data_summary['stats']}
            """
        else:
            data_context = f"""
            Full dataset preview:
            {df.head(10).to_string()}
            """
        
        # Enhanced system prompt for R
        system_prompt = f"""You are a helpful data analyst assistant using R.
        
        The user has uploaded a CSV file with the following information:
        {data_context}
        
        The data is loaded in an R dataframe called `df`.
        
        Guidelines:
        - Answer the user's question clearly and concisely
        - Write R code using base R, dplyr, ggplot2, gtsummary, and survival
        - For regression tables, use gtsummary's tbl_regression or tbl_summary
        - For visualizations, use ggplot2 and save plots using ggsave()
        - Always validate data before operations
        - Keep responses focused on the data and question
        - Summarize findings and insights
        
        When writing code:
        - The dataframe is available as 'df'
        - Libraries available: ggplot2, dplyr, gtsummary, survival, survminer, flextable
        - For survival plots, MUST load survminer: library(survminer) before using ggsurvplot()
        - For plots, save them using: ggsave("plot.png", width=10, height=6)
        - For ggsurvplot, save using: ggsave("plot.png", p$plot, width=10, height=6)
        - You can create multiple plots: plot1.png, plot2.png, etc.
        - For gtsummary tables, MUST save as HTML using flextable with pipe operator:
          table <- tbl_regression(model, exponentiate = TRUE)
          as_flex_table(table) %>% save_as_html(path = "table.html")
        - IMPORTANT: Use pipe operator (%>%) and path parameter in save_as_html()
        - Always add titles and labels to plots
        - Print results using print() or cat()
        
        Example code structure for tables:
        ```r
        # Cox regression model
        library(survival)
        library(gtsummary)
        library(flextable)
        
        model <- coxph(Surv(time, status) ~ age + sex, data = df)
        
        # Create and save table as HTML (CORRECT SYNTAX)
        table <- tbl_regression(model, exponentiate = TRUE)
        as_flex_table(table) %>% save_as_html(path = "table.html")
        
        # For summary tables
        summary_table <- tbl_summary(df, by = group_var)
        as_flex_table(summary_table) %>% save_as_html(path = "summary.html")
        
        # Alternative syntax also works:
        # save_as_html(as_flex_table(table), path = "table.html")
        ```
        
        Example for Kaplan-Meier plots:
        ```r
        # Kaplan-Meier survival analysis
        library(survival)
        library(survminer)
        
        # Fit survival model
        km_fit <- survfit(Surv(time, status) ~ treatment, data = df)
        
        # Create plot with ggsurvplot
        p <- ggsurvplot(
          km_fit,
          data = df,
          risk.table = TRUE,
          pval = TRUE,
          conf.int = TRUE,
          xlab = "Time",
          ylab = "Survival Probability",
          title = "Kaplan-Meier Curves"
        )
        
        # Save plot (note: use p$plot for ggsurvplot objects)
        ggsave("km_plot.png", p$plot, width = 10, height = 6)
        ```
        
        Example for plots:
        ```r
        # Visualization
        p <- ggplot(df, aes(x=x, y=y)) + 
          geom_point() +
          labs(title="My Plot", x="X axis", y="Y axis")
        
        ggsave("plot.png", p, width=10, height=6)
        ```
        """
        
        # Generate response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            with st.spinner("Analyzing your data with R..."):
                try:
                    messages = [{"role": "system", "content": system_prompt}]
                    
                    for msg in st.session_state.messages[-6:]:
                        content = msg["content"]
                        if len(content) > 500:
                            content = content[:500] + "..."
                        messages.append({"role": msg["role"], "content": content})
                    
                    messages.append({"role": "user", "content": user_input})
                    
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=messages,
                        temperature=0.1,
                        max_tokens=1500
                    )
                    
                    reply = response.choices[0].message.content
                    message_placeholder.markdown(reply)
                    
                    # Execute R code if present
                    if "```r" in reply or "```R" in reply:
                        code_blocks = reply.replace("```R", "```r").split("```r")
                        
                        for i in range(1, len(code_blocks)):
                            code = code_blocks[i].split("```")[0]
                            
                            # Create temp directory for this execution
                            with tempfile.TemporaryDirectory() as tmpdir:
                                # First attempt
                                result = run_r_code(code, df, tmpdir)
                                
                                # If failed, try to auto-fix (max 3 retries)
                                max_retries = 3
                                retry_count = 0
                                
                                while not result['success'] and retry_count < max_retries:
                                    retry_count += 1
                                    st.warning(f"⚠️ Execution failed. Auto-fixing code (Attempt {retry_count}/{max_retries})...")
                                    
                                    # Get fixed code from AI
                                    fixed_code = get_fixed_r_code(
                                        result['code'], 
                                        result['stderr'], 
                                        data_context
                                    )
                                    
                                    if fixed_code:
                                        st.info(f"🔧 Running fixed code...")
                                        result = run_r_code(fixed_code, df, tmpdir)
                                    else:
                                        st.warning("Could not generate fixed code. Stopping retries.")
                                        break
                                
                                if result['success']:
                                    # Display success message if retries were needed
                                    if retry_count > 0:
                                        st.success(f"✅ Code executed successfully after {retry_count} fix attempt(s)!")
                                    
                                    # Show the executed code
                                    st.subheader("📝 Executed R Code", divider="green")
                                    st.code(result['code'], language="r")
                                    
                                    # Display text output
                                    if result['stdout']:
                                        st.success("R Output:")
                                        st.text(result['stdout'])
                                    
                                    # Extract and display HTML tables
                                    html_tables = extract_html_from_output(tmpdir)
                                    if html_tables:
                                        st.success("📊 Table Output:")
                                    for html_content in html_tables:
                                        # Use a container with custom styling for better display
                                        st.markdown(html_content, unsafe_allow_html=True)
                                    
                                    # Look for saved plots
                                    plot_files = [f for f in os.listdir(tmpdir) if f.endswith('.png')]
                                    saved_plots = []
                                    
                                    for plot_file in plot_files:
                                        plot_path = os.path.join(tmpdir, plot_file)
                                        # Save to permanent location
                                        perm_dir = tempfile.mkdtemp()
                                        perm_path = os.path.join(perm_dir, plot_file)
                                        
                                        import shutil
                                        shutil.copy2(plot_path, perm_path)
                                        
                                        st.image(perm_path)
                                        saved_plots.append(perm_path)
                                    
                                    # Save to session state
                                    msg_data = {"role": "assistant", "content": reply}
                                    if result['stdout']:
                                        msg_data["output"] = result['stdout']
                                    if html_tables:
                                        msg_data["html_tables"] = html_tables
                                    if saved_plots:
                                        msg_data["plot_images"] = saved_plots
                                    if retry_count > 0:
                                        msg_data["fixed"] = True
                                        msg_data["retries"] = retry_count
                                    msg_data["code"] = result['code']  # Save code to session state
                                    
                                    st.session_state.messages.append(msg_data)
                                else:
                                    st.error(f"❌ R Execution Error (failed after {retry_count} fix attempt(s)):")
                                    st.code(result['stderr'], language="text")
                                    
                                    # Show the code that failed with subheader
                                    st.subheader("⚠️ Failed R Code", divider="red")
                                    st.code(result['code'], language="r")
                                    
                                    st.info("💡 Tips:\n- Try rephrasing your question\n- Check if column names are correct\n- Ensure data types are appropriate")
                                    
                                    st.session_state.messages.append({
                                        "role": "assistant",
                                        "content": reply,
                                        "code": result['code'],  # Save failed code too
                                        "error": result['stderr']
                                    })
                    else:
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": reply
                        })
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    st.info("Please try again or rephrase your question.")
else:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.info("👈 Please upload a CSV file to start")
        
        st.markdown("### 💡 Example questions you can ask:")
        st.markdown("""
        - What are the main trends in my data?
        - Show me a correlation plot
        - Create a bar chart of the top 10 categories
        - What's the average value by month?
        - Run a Cox regression model and show results
        - Create a summary table of demographics
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 12px;'>
💡 Powered by R, ggplot2, gtsummary, survminer, and flextable | 
🔒 Your data stays private and is not stored |
⚙️ Requires R and packages (ggplot2, dplyr, gtsummary, survival, survminer, flextable) installed
</div>
""", unsafe_allow_html=True)
