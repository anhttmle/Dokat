/**
 * Entry point for React Native (iOS & Android).
 *
 * Registers the root App component with the app name defined in
 * ios/Dokat/Info.plist → CFBundleDisplayName ("Dokat").
 */
import { AppRegistry } from 'react-native';
import App from './App';

AppRegistry.registerComponent('Dokat', () => App);
