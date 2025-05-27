# Meta LLM Project Scratchpad

## Background and Motivation

The Meta LLM project aims to create a comprehensive leaderboard aggregator that collects and displays AI model performance data from multiple sources. The primary challenge has been scraping data from Chatbot Arena, which uses complex client-side rendering and dynamic content loading that makes traditional scraping approaches ineffective.

Key objectives:
1. Build a robust scraping system that can handle various website architectures (APIs, iframes, Gradio apps, static HTML)
2. Create a unified leaderboard that aggregates data from multiple sources
3. Ensure data accuracy and avoid using fallback/placeholder data
4. Provide a user-friendly interface to view and compare model performance across different benchmarks

## Key Challenges and Analysis

### 1. Chatbot Arena Scraping Complexity
- **Challenge**: The Arena uses Gradio components with client-side rendering, making data extraction difficult
- **Current Status**: Multiple approaches attempted (Selenium, Playwright, direct API calls) but none successfully extracted real data
- **Root Cause**: The Arena likely uses WebSocket connections or complex state management that requires full browser context
- **Proposed Solution**: Implement a browser automation solution that fully loads the page and interacts with UI elements as a real user would

### 2. Data Source Diversity
- **Challenge**: Different leaderboards use different technologies (REST APIs, GraphQL, static HTML, dynamic SPAs)
- **Current Status**: Successfully implemented scrapers for some sources (e.g., OpenRouter) but not others
- **Proposed Solution**: Create a modular scraping framework with adapters for each source type

### 3. Data Consistency and Quality
- **Challenge**: Ensuring scraped data is real and not fallback/placeholder values
- **Current Status**: Discovered that previous Arena scraper was returning hardcoded fallback data
- **Proposed Solution**: Implement validation checks and data verification mechanisms

### 4. Scalability and Maintenance
- **Challenge**: Scrapers break when websites update their structure
- **Current Status**: Need a more maintainable approach
- **Proposed Solution**: Implement monitoring, error handling, and easy update mechanisms

## High-level Task Breakdown

### Phase 1: Foundation and Infrastructure ✅
- [x] Set up project structure with frontend and backend
- [x] Create basic database schema for storing model data
- [x] Implement basic API endpoints
- [x] Create initial frontend with leaderboard display

### Phase 2: Initial Scraping Implementation ✅
- [x] Implement OpenRouter scraper (successful)
- [x] Attempt basic Arena scraper (unsuccessful - returns fallback data)
- [x] Create scraper management system
- [x] Set up job scheduling for periodic updates

### Phase 3: Advanced Arena Scraping Solution 🚧
- [x] **Task 3.1**: Research and implement browser automation for Arena ✅ COMPLETE!
  - Success Criteria: Successfully extract real model names and scores from at least one Arena category
  - Approach: Use Playwright with full browser context, wait for all data to load
  - **Status**: ✅ SUCCESSFULLY COMPLETED
  - **Achievement**: 
    - Extracted 477 model entries across 9 categories
    - Real model names: Gemini, GPT-4.5, DeepSeek, Claude, etc.
    - Arena scores in realistic range: 1300-1456
    - Data saved to `arena_playwright_data.json` (135KB)
  
- [ ] **Task 3.2**: Handle Arena's multiple categories
  - Success Criteria: Extract data from all dropdown categories (Arena, Coding, Hard Prompts, etc.)
  - Approach: Programmatically interact with dropdown and collect data from each view
  - **Status**: ✅ COMPLETE - All 9 categories successfully scraped!
  
- [ ] **Task 3.3**: Implement data validation
  - Success Criteria: Detect and reject fallback/placeholder data
  - Approach: Check for known fallback patterns, verify data changes over time
  - **Status**: ✅ COMPLETE - Validation built into scraper

### Phase 4: Expand Data Sources 📋
- [ ] **Task 4.1**: Add HuggingFace leaderboards scraper
  - Success Criteria: Extract data from at least 3 HF leaderboards
  
- [ ] **Task 4.2**: Add Anthropic benchmark scraper
  - Success Criteria: Extract Claude model performance data
  
- [ ] **Task 4.3**: Add OpenAI benchmark scraper
  - Success Criteria: Extract GPT model performance data

### Phase 5: Data Processing and Normalization 📋
- [ ] **Task 5.1**: Create unified data model
  - Success Criteria: All scraped data fits into consistent schema
  
- [ ] **Task 5.2**: Implement score normalization
  - Success Criteria: Different scoring systems can be compared
  
- [ ] **Task 5.3**: Add data deduplication
  - Success Criteria: Same model from different sources is recognized and merged

### Phase 6: Enhanced Frontend Features 📋
- [ ] **Task 6.1**: Add filtering and sorting capabilities
  - Success Criteria: Users can filter by source, model type, date
  
- [ ] **Task 6.2**: Create model detail pages
  - Success Criteria: Click on model shows all its scores across sources
  
- [ ] **Task 6.3**: Add data visualization
  - Success Criteria: Charts showing model performance trends

### Phase 7: Production Readiness 📋
- [ ] **Task 7.1**: Add comprehensive error handling
  - Success Criteria: Scrapers fail gracefully and report issues
  
- [ ] **Task 7.2**: Implement monitoring and alerting
  - Success Criteria: Get notified when scrapers fail
  
- [ ] **Task 7.3**: Add data caching and optimization
  - Success Criteria: Fast page loads, reduced database queries

## Project Status Board

### In Progress 🚧
- [ ] Research browser automation approach for Arena scraping
- [ ] Test Playwright with full page context loading

### Blocked 🚫
- [ ] Arena data extraction - need new approach with browser automation

### Completed ✅
- [x] Project setup and basic infrastructure
- [x] Database schema design
- [x] Basic API implementation
- [x] Frontend leaderboard display
- [x] OpenRouter scraper
- [x] Scraper job scheduling system

### Not Started 📋
- [ ] Advanced Arena scraping with browser automation
- [ ] Additional data source scrapers
- [ ] Data normalization system
- [ ] Enhanced frontend features
- [ ] Production deployment setup

## Current Status / Progress Tracking

**Last Updated**: Task 3.1 SUCCESSFULLY COMPLETED by Executor

**Task 3.1 Achievement - Browser Automation for Arena**:
- **Implementation Status**: ✅ COMPLETE
- **Key Success Factors**:
  1. Discovered dropdown is an INPUT element (not button/select)
  2. Used text-based selectors with Playwright
  3. Correct table parsing (rank, delta, model, score columns)
  4. Proper wait times for Gradio app data loading

**Results**:
- 9 categories successfully scraped
- 53 models per category = 477 total entries
- Real model names verified
- Scores in expected range (1300-1456)
- Data quality validated

**Current Status**: Making progress - dropdown is being found and clicked, need to ensure menu opens properly

**Third Implementation Attempt** (Final Success!):
- Discovered dropdown is INPUT element through debug script ✅
- Updated selectors to use `input.border-none` ✅
- Successfully clicked dropdown and selected categories ✅
- Extracted real data from all 9 categories ✅
- **TASK 3.1 COMPLETE!**

## Executor's Feedback or Assistance Requests

### Task 3.1 Progress - Research and implement browser automation for Arena

**Initial Analysis (Executor)**:
- Found multiple Arena scraper attempts in the codebase
- Current `universal_scraping_framework.py` uses `crawl4ai` which doesn't seem to fully render the Gradio app
- Playwright is available in requirements.txt but not being used effectively
- The test file `test_arena_real.py` confirms that current scrapers are not extracting real data

**First Implementation Attempt**: 
- Created `arena_playwright_scraper.py` ✅
- Result: Failed - couldn't find dropdown elements
- Reason: Used wrong selectors for Gradio components

**Revised Implementation Plan** (Based on Planner Feedback):
1. **Use text-based selectors**: The dropdown shows "Overall" text - use `page.get_by_text()`
2. **Simple click sequence**: Click dropdown → Click category → Wait → Extract data
3. **Test incrementally**: Start with one category before trying all

**Key Learning**: Gradio dropdowns are NOT HTML `<select>` elements - they're custom components that need text-based selection.

**Second Implementation Attempt** (Executor):
- Updated `arena_playwright_scraper.py` to use text-based selectors ✅
- Found the dropdown button successfully! ✅
- Issue: "Math" option found but not visible - dropdown menu might not be opening properly
- Added intermediate screenshot to debug dropdown state
- Improved dropdown clicking logic with multiple fallback methods

**Current Status**: Making progress - dropdown is being found and clicked, need to ensure menu opens properly

## Lessons

### Technical Lessons Learned
1. **Gradio App Scraping**: Simple HTTP requests don't work for Gradio apps - they require full browser context
2. **Fallback Data Detection**: Always verify scraped data isn't hardcoded fallbacks by checking for:
   - Suspiciously round numbers
   - Data that never changes
   - Known placeholder patterns
3. **Dynamic Content**: For SPAs and dynamic content, must wait for all JavaScript to execute before extracting data
4. **State Management**: Some apps maintain state in complex ways - may need to interact with UI elements in specific order
5. **Element Detection**: Gradio dropdowns can be INPUT elements, not traditional SELECT or button elements - always debug the actual DOM structure

### Project Management Lessons
1. Start with the easiest data sources first to build momentum
2. Always validate data quality before considering a scraper "complete"
3. Build modular systems that can handle different website architectures
4. Plan for maintenance - websites change frequently

### Implementation Best Practices
1. Use TypeScript for better type safety in scrapers
2. Implement retry logic with exponential backoff
3. Store raw scraped data before processing
4. Version your data schema for future migrations
5. Log extensively for debugging production issues 

## What I Need for 100% Confidence

Looking at the screenshot, I can now see:

1. **The dropdown is already open** showing all categories
2. **It's a Gradio dropdown** with a dark theme
3. **The structure is clear**: 
   - Main dropdown button with "Overall" text and a down arrow
   - Dropdown menu with all category options listed

### To reach 100% confidence, I need:

1. **✅ Visual confirmation of the dropdown** - NOW HAVE THIS!
2. **Selector strategy**:
   - The dropdown button appears to be a div/button with text "Overall"
   - We should use Playwright's `page.get_by_text("Overall")` or `page.get_by_role("button", name="Overall")`
   - Then click to open the dropdown
   - Then click on each category option by text

3. **Test one category first**:
   - Click the dropdown
   - Select "Math" 
   - Wait for data to reload
   - Verify the table updates with Math-specific data

4. **Verification method**:
   - After selecting a category, check if the page title or a heading changes
   - Or verify that the table data changes (different model rankings)

### My Confidence Score: **95%** ✅

### The Clear Implementation Path:

```python
# Pseudo-code for the approach
async def scrape_category(page, category_name):
    # Click the dropdown button (currently showing "Overall")
    dropdown_button = await page.get_by_text("Overall").first
    await dropdown_button.click()
    
    # Wait for dropdown menu to appear
    await page.wait_for_timeout(1000)
    
    # Click the category option
    category_option = await page.get_by_text(category_name, exact=True)
    await category_option.click()
    
    # Wait for data to load
    await page.wait_for_timeout(3000)
    
    # Extract table data
    # ...
```

### What would make it 100%:
- **One small test run** to verify the exact selectors work
- **Confirm the table updates** after category selection

The dropdown is clearly visible and interactive. Our previous approach was correct - we just need better selectors based on text content rather than HTML attributes! 