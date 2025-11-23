const HtmlWebpackPlugin = require('html-webpack-plugin');
const { ModuleFederationPlugin } = require('webpack').container;
const path = require('path');

module.exports = (env, argv) => {
  const isProduction = argv.mode === 'production';

  return {
    entry: './src/index.tsx',
    mode: isProduction ? 'production' : 'development',
    devtool: isProduction ? 'source-map' : 'eval-source-map',
    
    output: {
      path: path.resolve(__dirname, 'dist'),
      filename: '[name].[contenthash].js',
      publicPath: 'auto',
      clean: true,
    },

    resolve: {
      extensions: ['.tsx', '.ts', '.js', '.jsx'],
      alias: {
        '@odin/shared': path.resolve(__dirname, '../packages/shared/src'),
      },
    },

    module: {
      rules: [
        {
          test: /\.tsx?$/,
          use: 'ts-loader',
          exclude: /node_modules/,
        },
        {
          test: /\.css$/,
          use: ['style-loader', 'css-loader'],
        },
      ],
    },

    plugins: [
      new ModuleFederationPlugin({
        name: 'portal',
        filename: 'remoteEntry.js',
        remotes: {
          health: 'health@/mfe/health/remoteEntry.js',
          data: 'data@/mfe/data/remoteEntry.js',
          confluence: 'confluence@/mfe/confluence/remoteEntry.js',
          files: 'files@/mfe/files/remoteEntry.js',
          llm: 'llm@/mfe/llm/remoteEntry.js',
          logs: 'logs@/mfe/logs/remoteEntry.js',
          secrets: 'secrets@/mfe/secrets/remoteEntry.js',
          messages: 'messages@/mfe/messages/remoteEntry.js',
          imageAnalysis: 'imageAnalysis@/mfe/image-analysis/remoteEntry.js',
        },
        shared: {
          react: {
            singleton: true,
            requiredVersion: '^18.2.0',
          },
          'react-dom': {
            singleton: true,
            requiredVersion: '^18.2.0',
          },
          'react-router-dom': {
            singleton: true,
            requiredVersion: '^6.20.1',
          },
        },
      }),
      new HtmlWebpackPlugin({
        template: './public/index.html',
        favicon: './public/favicon.ico',
      }),
    ],

    devServer: {
      port: 3000,
      hot: true,
      historyApiFallback: true,
      proxy: {
        '/api': {
          target: 'http://localhost',
          changeOrigin: true,
        },
        '/mfe': {
          target: 'http://localhost',
          changeOrigin: true,
        },
      },
    },

    optimization: {
      splitChunks: {
        chunks: 'all',
      },
    },
  };
};

