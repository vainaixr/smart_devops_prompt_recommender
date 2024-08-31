import React, { useState, useEffect } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { coy } from 'react-syntax-highlighter/dist/esm/styles/prism';
import './App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [apiCallCount, setApiCallCount] = useState(0);
  const [lastApiCallLength, setLastApiCallLength] = useState(0);
  const [showStats, setShowStats] = useState(false);
  const [chatWidth, setChatWidth] = useState(50);
  const [topK, setTopK] = useState(5);
  const [weights, setWeights] = useState({
    distance: 15.9,
    time_elapsed_since_added: 2,
    length: 0.05,
    retrieval_count: 1
  });
  const [distanceFilter, setDistanceFilter] = useState(0.5); // New state variable for distance filter
  const [showDropdown, setShowDropdown] = useState(false);

  useEffect(() => {
    if (input.length >= 5 && input.length % 5 === 0) {
      fetchSuggestions(input);
    }
  }, [input]);

  const fetchSuggestions = async (input) => {
    if (input.trim().length < 5 || input.trim().length === lastApiCallLength) return;

    setLastApiCallLength(input.trim().length);
    setApiCallCount(apiCallCount + 1);

    const response = await fetch('http://localhost:8000/recommender', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message: input, top_n: topK, weights, distance_filter: distanceFilter }), // Include distance filter
    });

    const data = await response.json();
    setSuggestions(data);
  };

  const sendMessage = async (message, isSuggestion = false, suggestionResponse = '') => {
    if (!message.trim()) return;

    const userMessage = { sender: 'user', text: message };
    setMessages((prevMessages) => [...prevMessages, userMessage]);

    if (isSuggestion) {
      const botMessage = { sender: 'bot', text: suggestionResponse };
      setMessages((prevMessages) => [...prevMessages, botMessage]);
    } else {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message }),
      });

      const data = await response.json();
      const botMessage = { sender: 'bot', text: data.response };
      setMessages((prevMessages) => [...prevMessages, botMessage]);
    }

    setInput('');
    setSuggestions([]);
  };

  const renderMessage = (msg) => {
    const codeBlockRegex = /```([\s\S]*?)```/g;
    const parts = msg.text.split(codeBlockRegex);
    return parts.map((part, index) => {
      if (index % 2 === 1) {
        return (
          <SyntaxHighlighter key={index} language="javascript" style={coy}>
            {part}
          </SyntaxHighlighter>
        );
      }
      return <span key={index}>{part}</span>;
    });
  };

  const formatDate = (timestamp) => {
    const date = new Date(timestamp * 1000);
    const options = { year: 'numeric', month: 'short', day: '2-digit' };
    return date.toLocaleDateString('en-US', options).replace(/ /g, '-');
  };

  const formatNumber = (num) => {
    return num.toFixed(3);
  };

  const getHighlightClass = (value) => {
    if (value >= 0.75) return 'high';
    if (value >= 0.5) return 'medium';
    return 'low';
  };

  const capitalizeFirstLetter = (feature) => {
    const featuresToCapitalize = ['distance', 'time_elapsed_since_added', 'length', 'retrieval_count'];
    if (featuresToCapitalize.includes(feature.toLowerCase())) {
      return feature.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase());
    }
    return feature;
  };

  const handleMouseDown = (e) => {
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  const handleMouseMove = (e) => {
    const newChatWidth = (e.clientX / window.innerWidth) * 100;
    if (newChatWidth > 10 && newChatWidth < 90) {
      setChatWidth(newChatWidth);
    }
  };

  const handleMouseUp = () => {
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
  };

  const handleWeightChange = (e) => {
    const { name, value } = e.target;
    setWeights((prevWeights) => ({
      ...prevWeights,
      [name]: Number(value)
    }));
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pastedText = e.clipboardData.getData('Text');
    setInput(pastedText);
    fetchSuggestions(pastedText);
  };

  return (
    <div className="App">
      <div className="chat-container" style={{ gridTemplateColumns: `${chatWidth}% 5px ${100 - chatWidth}%` }}>
        <div className="messages">
          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.sender}`}>
              {msg.sender === 'bot' ? (
                <div dangerouslySetInnerHTML={{ __html: msg.text }} />
              ) : (
                renderMessage(msg)
              )}
            </div>
          ))}
          <div className="input-container">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onPaste={handlePaste}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage(input)}
            />
            <button onClick={() => sendMessage(input)}>Send</button>
          </div>
        </div>
        <div className="divider" onMouseDown={handleMouseDown}></div>
        <div className="suggestions">
          <h2 className="recommendations-heading">Top-k Recommendations</h2> {/* Changed heading here */}
          {suggestions.length > 0 && (
            suggestions.map((suggestion, index) => (
              <div key={index} className="suggestion">
                <strong>Prompt:</strong> {suggestion.prompt}<br />
                <strong>Response:</strong><div dangerouslySetInnerHTML={{ __html: suggestion.response }} /><br />
                <div className="button-container">
                  <button onClick={() => sendMessage(suggestion.prompt, true, suggestion.response)}>Submit this prompt</button>
                  <button onClick={() => setShowStats(!showStats)}>Show Recommendation Stats</button>
                </div>
                {showStats && (
                  <table className="feature-table">
                    <thead>
                      <tr>
                        <th>Feature</th>
                        <th>Value</th>
                        <th>Score</th>
                        <th>Weight</th>
                        <th>Contribution</th>
                      </tr>
                    </thead>
                    <tbody>
                      {suggestion.contributions.map((contribution, idx) => (
                        <tr key={idx} className={getHighlightClass(contribution.score)}>
                          <td className="capitalize">{capitalizeFirstLetter(contribution.feature)}</td>
                          <td>{contribution.feature === 'time_elapsed_since_added' ? suggestion.time_elapsed : contribution.value}</td>
                          <td>{formatNumber(contribution.score)}</td>
                          <td>{formatNumber(contribution.weight)}</td>
                          <td>{formatNumber(contribution.contribution)}</td>
                        </tr>
                      ))}
                      <tr className="final-score">
                        <td colSpan="4">Final Score</td>
                        <td>{formatNumber(suggestion.weighted_score)}</td>
                      </tr>
                    </tbody>
                  </table>
                )}
              </div>
            ))
          )}
        </div>
        <div className="api-call-counter">
          <strong>API Calls Made:</strong> {apiCallCount}
        </div>
      </div>
      <button className="settings-button" onClick={() => setShowDropdown(!showDropdown)}>Settings</button>
      {showDropdown && (
        <div className="dropdown">
          <label htmlFor="topK">Top K:</label>
          <input
            type="number"
            id="topK"
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
            min="1"
            step="1"
          />
          <label htmlFor="distanceWeight">Distance Weight:</label>
          <input
            type="number"
            id="distanceWeight"
            name="distance"
            value={weights.distance}
            onChange={handleWeightChange}
            step="0.1"
          />
          <label htmlFor="timeElapsedWeight">Time Elapsed Weight:</label>
          <input
            type="number"
            id="timeElapsedWeight"
            name="time_elapsed_since_added"
            value={weights.time_elapsed_since_added}
            onChange={handleWeightChange}
            step="0.1"
          />
          <label htmlFor="lengthWeight">Length Weight:</label>
          <input
            type="number"
            id="lengthWeight"
            name="length"
            value={weights.length}
            onChange={handleWeightChange}
            step="0.1"
          />
          <label htmlFor="retrievalCountWeight">Retrieval Count Weight:</label>
          <input
            type="number"
            id="retrievalCountWeight"
            name="retrieval_count"
            value={weights.retrieval_count}
            onChange={handleWeightChange}
            step="0.1"
          />
          <label htmlFor="distanceFilter">Distance Filter:</label>
          <input
            type="number"
            id="distanceFilter"
            value={distanceFilter}
            onChange={(e) => setDistanceFilter(Number(e.target.value))}
            step="0.1"
            min="0"
            max="1"
          />
        </div>
      )}
    </div>
  );
}

export default App;
